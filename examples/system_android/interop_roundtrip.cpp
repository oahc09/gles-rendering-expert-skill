// SPDX-License-Identifier: MIT
// Android API26 native CLI. Vulkan clear -> native fence -> GLES read/write ->
// native fence -> Vulkan readback. No protected buffers; no fd-memory assumption.
#define VK_USE_PLATFORM_ANDROID_KHR
#include <vulkan/vulkan.h>
#include <android/hardware_buffer.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <GLES2/gl2ext.h>
#include <unistd.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
struct Unsupported : std::runtime_error { using std::runtime_error::runtime_error; };
void need(bool ok,const char* why) { if(!ok) throw std::runtime_error(why); }
void supported(bool ok,const char* why) { if(!ok) throw Unsupported(why); }
void vkcheck(VkResult r,const char* why) { need(r==VK_SUCCESS,why); }
bool token(const char* list,const char* name) {
 if(!list)return false; std::string s=" "+std::string(list)+" ";return s.find(" "+std::string(name)+" ")!=std::string::npos;
}
struct Fd {int value=-1; ~Fd(){if(value>=0)close(value);} int take(){int x=value;value=-1;return x;} };
struct Lab {
 EGLDisplay display=EGL_NO_DISPLAY; EGLContext context=EGL_NO_CONTEXT; EGLSurface surface=EGL_NO_SURFACE;
 EGLImageKHR image=EGL_NO_IMAGE_KHR; GLuint texture=0,fbo=0;
 PFNEGLCREATEIMAGEKHRPROC createImage=nullptr; PFNEGLDESTROYIMAGEKHRPROC destroyImage=nullptr;
 PFNEGLCREATESYNCKHRPROC createSync=nullptr; PFNEGLDESTROYSYNCKHRPROC destroySync=nullptr;
 PFNEGLWAITSYNCKHRPROC waitSync=nullptr; PFNEGLDUPNATIVEFENCEFDANDROIDPROC duplicate=nullptr;
 PFNEGLGETNATIVECLIENTBUFFERANDROIDPROC clientBuffer=nullptr; PFNGLEGLIMAGETARGETTEXTURE2DOESPROC imageTarget=nullptr;
 AHardwareBuffer* ahb=nullptr; VkInstance instance{};VkPhysicalDevice physical{};VkDevice device{};VkQueue queue{};uint32_t family=0;
 VkImage vkImage{};VkDeviceMemory memory{},readMemory{};VkBuffer readBuffer{};VkCommandPool pool{};VkCommandBuffer command{};
 VkSemaphore produced{},consumed{};VkFence completed{};bool mapped=false;void* address=nullptr;
 PFN_vkGetPhysicalDeviceExternalSemaphoreProperties semaphoreProperties=nullptr;
 PFN_vkGetPhysicalDeviceImageFormatProperties2 imageProperties=nullptr;
 PFN_vkGetAndroidHardwareBufferPropertiesANDROID ahbProperties=nullptr;
 PFN_vkGetSemaphoreFdKHR getFd=nullptr;PFN_vkImportSemaphoreFdKHR importFd=nullptr;
 ~Lab(){
  if(device)vkDeviceWaitIdle(device);
  if(display!=EGL_NO_DISPLAY && context!=EGL_NO_CONTEXT && eglMakeCurrent(display,surface,surface,context)) {
   glFinish();if(fbo)glDeleteFramebuffers(1,&fbo);if(texture)glDeleteTextures(1,&texture);
  }
  if(image!=EGL_NO_IMAGE_KHR && destroyImage)destroyImage(display,image);
  if(device){if(mapped)vkUnmapMemory(device,readMemory);if(completed)vkDestroyFence(device,completed,nullptr);
   if(produced)vkDestroySemaphore(device,produced,nullptr);if(consumed)vkDestroySemaphore(device,consumed,nullptr);
   if(pool)vkDestroyCommandPool(device,pool,nullptr);if(readBuffer)vkDestroyBuffer(device,readBuffer,nullptr);
   if(readMemory)vkFreeMemory(device,readMemory,nullptr);if(vkImage)vkDestroyImage(device,vkImage,nullptr);
   if(memory)vkFreeMemory(device,memory,nullptr);vkDestroyDevice(device,nullptr);}
  if(instance)vkDestroyInstance(instance,nullptr);if(ahb)AHardwareBuffer_release(ahb);
  if(display!=EGL_NO_DISPLAY){eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
   if(surface!=EGL_NO_SURFACE)eglDestroySurface(display,surface);if(context!=EGL_NO_CONTEXT)eglDestroyContext(display,context);eglTerminate(display);}
 }
 template<typename T>T eglfn(const char* name){auto f=reinterpret_cast<T>(eglGetProcAddress(name));supported(f!=nullptr,"missing EGL entry point");return f;}
 void eglInit(){
  display=eglGetDisplay(EGL_DEFAULT_DISPLAY);supported(display!=EGL_NO_DISPLAY&&eglInitialize(display,nullptr,nullptr),"EGL unavailable");
  need(eglBindAPI(EGL_OPENGL_ES_API),"bind GLES");
  EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};
  EGLConfig config{};EGLint count=0; supported(eglChooseConfig(display,attrs,&config,1,&count)&&count>0,"no ES3 pbuffer config");
  EGLint ca[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};context=eglCreateContext(display,config,EGL_NO_CONTEXT,ca);
  EGLint sa[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};surface=eglCreatePbufferSurface(display,config,sa);
  supported(context!=EGL_NO_CONTEXT&&surface!=EGL_NO_SURFACE&&eglMakeCurrent(display,surface,surface,context),"ES3 context unavailable");
  const char* ex=eglQueryString(display,EGL_EXTENSIONS);
  for(const char* s:{"EGL_ANDROID_image_native_buffer","EGL_ANDROID_get_native_client_buffer","EGL_KHR_image_base","EGL_ANDROID_native_fence_sync","EGL_KHR_wait_sync"})supported(token(ex,s),s);
  GLint n=0;glGetIntegerv(GL_NUM_EXTENSIONS,&n);bool imageExt=false;for(GLint i=0;i<n;++i)imageExt|=std::strcmp(reinterpret_cast<const char*>(glGetStringi(GL_EXTENSIONS,i)),"GL_OES_EGL_image")==0;
  supported(imageExt,"GL_OES_EGL_image absent");
  createImage=eglfn<PFNEGLCREATEIMAGEKHRPROC>("eglCreateImageKHR");destroyImage=eglfn<PFNEGLDESTROYIMAGEKHRPROC>("eglDestroyImageKHR");
  createSync=eglfn<PFNEGLCREATESYNCKHRPROC>("eglCreateSyncKHR");destroySync=eglfn<PFNEGLDESTROYSYNCKHRPROC>("eglDestroySyncKHR");waitSync=eglfn<PFNEGLWAITSYNCKHRPROC>("eglWaitSyncKHR");
  duplicate=eglfn<PFNEGLDUPNATIVEFENCEFDANDROIDPROC>("eglDupNativeFenceFDANDROID");clientBuffer=eglfn<PFNEGLGETNATIVECLIENTBUFFERANDROIDPROC>("eglGetNativeClientBufferANDROID");imageTarget=eglfn<PFNGLEGLIMAGETARGETTEXTURE2DOESPROC>("glEGLImageTargetTexture2DOES");
 }
 uint32_t type(uint32_t bits,VkMemoryPropertyFlags flags){VkPhysicalDeviceMemoryProperties p{};vkGetPhysicalDeviceMemoryProperties(physical,&p);for(uint32_t i=0;i<p.memoryTypeCount;++i)if((bits&(1u<<i))&&(p.memoryTypes[i].propertyFlags&flags)==flags)return i;throw Unsupported("required memory type absent");}
 void vkInit(){
  auto version=reinterpret_cast<PFN_vkEnumerateInstanceVersion>(vkGetInstanceProcAddr(VK_NULL_HANDLE,"vkEnumerateInstanceVersion"));uint32_t v=0;supported(version&&version(&v)==VK_SUCCESS&&v>=VK_API_VERSION_1_1,"Vulkan1.1 unavailable");
  VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};app.pApplicationName="GLES interoperability validation";app.apiVersion=VK_API_VERSION_1_1;
  VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ci.pApplicationInfo=&app;vkcheck(vkCreateInstance(&ci,nullptr,&instance),"create Vulkan instance");
  uint32_t count=0;vkcheck(vkEnumeratePhysicalDevices(instance,&count,nullptr),"enumerate device count");supported(count>0,"no physical Vulkan device");std::vector<VkPhysicalDevice> ps(count);vkcheck(vkEnumeratePhysicalDevices(instance,&count,ps.data()),"enumerate devices");
  const std::array<const char*,3> required={VK_ANDROID_EXTERNAL_MEMORY_ANDROID_HARDWARE_BUFFER_EXTENSION_NAME,VK_KHR_EXTERNAL_SEMAPHORE_FD_EXTENSION_NAME,VK_EXT_QUEUE_FAMILY_FOREIGN_EXTENSION_NAME};
  for(auto p:ps){VkPhysicalDeviceProperties props{};vkGetPhysicalDeviceProperties(p,&props);if(props.apiVersion<VK_API_VERSION_1_1)continue;
   uint32_t ec=0;vkcheck(vkEnumerateDeviceExtensionProperties(p,nullptr,&ec,nullptr),"extension count");std::vector<VkExtensionProperties> es(ec);vkcheck(vkEnumerateDeviceExtensionProperties(p,nullptr,&ec,es.data()),"extensions");
   bool ok=true;for(auto name:required)ok&=std::any_of(es.begin(),es.end(),[&](const auto&e){return std::strcmp(e.extensionName,name)==0;});if(!ok)continue;
   uint32_t qc=0;vkGetPhysicalDeviceQueueFamilyProperties(p,&qc,nullptr);std::vector<VkQueueFamilyProperties> qs(qc);vkGetPhysicalDeviceQueueFamilyProperties(p,&qc,qs.data());for(uint32_t i=0;i<qc;++i)if(qs[i].queueFlags&VK_QUEUE_GRAPHICS_BIT){physical=p;family=i;break;}if(physical)break;
  }supported(physical!=VK_NULL_HANDLE,"AHB/fence/foreign-capable Vulkan device unavailable");
  semaphoreProperties=reinterpret_cast<PFN_vkGetPhysicalDeviceExternalSemaphoreProperties>(vkGetInstanceProcAddr(instance,"vkGetPhysicalDeviceExternalSemaphoreProperties"));imageProperties=reinterpret_cast<PFN_vkGetPhysicalDeviceImageFormatProperties2>(vkGetInstanceProcAddr(instance,"vkGetPhysicalDeviceImageFormatProperties2"));supported(semaphoreProperties&&imageProperties,"Vulkan1.1 instance commands unavailable");
  VkPhysicalDeviceExternalSemaphoreInfo si{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_SEMAPHORE_INFO};si.handleType=VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT;
  VkExternalSemaphoreProperties sp{VK_STRUCTURE_TYPE_EXTERNAL_SEMAPHORE_PROPERTIES};semaphoreProperties(physical,&si,&sp);
  constexpr auto sf=VK_EXTERNAL_SEMAPHORE_FEATURE_IMPORTABLE_BIT|VK_EXTERNAL_SEMAPHORE_FEATURE_EXPORTABLE_BIT;supported((sp.externalSemaphoreFeatures&sf)==sf,"SYNC_FD import/export unsupported");
  float priority=1;VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
  VkDeviceCreateInfo dc{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dc.queueCreateInfoCount=1;dc.pQueueCreateInfos=&qi;dc.enabledExtensionCount=required.size();dc.ppEnabledExtensionNames=required.data();vkcheck(vkCreateDevice(physical,&dc,nullptr,&device),"create device");vkGetDeviceQueue(device,family,0,&queue);
  ahbProperties=reinterpret_cast<PFN_vkGetAndroidHardwareBufferPropertiesANDROID>(vkGetDeviceProcAddr(device,"vkGetAndroidHardwareBufferPropertiesANDROID"));getFd=reinterpret_cast<PFN_vkGetSemaphoreFdKHR>(vkGetDeviceProcAddr(device,"vkGetSemaphoreFdKHR"));importFd=reinterpret_cast<PFN_vkImportSemaphoreFdKHR>(vkGetDeviceProcAddr(device,"vkImportSemaphoreFdKHR"));supported(ahbProperties&&getFd&&importFd,"missing Vulkan extension entrypoint");
 }
 void allocate(){
  constexpr auto usage=VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT|VK_IMAGE_USAGE_SAMPLED_BIT|VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
  VkPhysicalDeviceExternalImageFormatInfo ext{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTERNAL_IMAGE_FORMAT_INFO};ext.handleType=VK_EXTERNAL_MEMORY_HANDLE_TYPE_ANDROID_HARDWARE_BUFFER_BIT_ANDROID;
  VkPhysicalDeviceImageFormatInfo2 fi{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_IMAGE_FORMAT_INFO_2};fi.pNext=&ext;fi.format=VK_FORMAT_R8G8B8A8_UNORM;fi.type=VK_IMAGE_TYPE_2D;fi.tiling=VK_IMAGE_TILING_OPTIMAL;fi.usage=usage;
  VkAndroidHardwareBufferUsageANDROID au{VK_STRUCTURE_TYPE_ANDROID_HARDWARE_BUFFER_USAGE_ANDROID};VkExternalImageFormatProperties ep{VK_STRUCTURE_TYPE_EXTERNAL_IMAGE_FORMAT_PROPERTIES};ep.pNext=&au;VkImageFormatProperties2 fp{VK_STRUCTURE_TYPE_IMAGE_FORMAT_PROPERTIES_2};fp.pNext=&ep;
  supported(imageProperties(physical,&fi,&fp)==VK_SUCCESS,"RGBA8 AHB image usage unsupported");supported(ep.externalMemoryProperties.externalMemoryFeatures&VK_EXTERNAL_MEMORY_FEATURE_IMPORTABLE_BIT,"AHB not importable");
  AHardwareBuffer_Desc desc{};desc.width=16;desc.height=16;desc.layers=1;desc.format=AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM;desc.usage=au.androidHardwareBufferUsage|AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE|AHARDWAREBUFFER_USAGE_GPU_FRAMEBUFFER;
  supported(!(desc.usage&AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT),"protected resources forbidden in readback lab");supported(AHardwareBuffer_allocate(&desc,&ahb)==0&&ahb,"AHB allocation unsupported");
  VkAndroidHardwareBufferFormatPropertiesANDROID format{VK_STRUCTURE_TYPE_ANDROID_HARDWARE_BUFFER_FORMAT_PROPERTIES_ANDROID};VkAndroidHardwareBufferPropertiesANDROID ap{VK_STRUCTURE_TYPE_ANDROID_HARDWARE_BUFFER_PROPERTIES_ANDROID};ap.pNext=&format;vkcheck(ahbProperties(device,ahb,&ap),"AHB properties");supported(format.format==VK_FORMAT_R8G8B8A8_UNORM,"unexpected external format");
  VkExternalMemoryImageCreateInfo ei{VK_STRUCTURE_TYPE_EXTERNAL_MEMORY_IMAGE_CREATE_INFO};ei.handleTypes=ext.handleType;
  VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};ii.pNext=&ei;ii.imageType=VK_IMAGE_TYPE_2D;ii.format=fi.format;ii.extent={16,16,1};ii.mipLevels=1;ii.arrayLayers=1;ii.samples=VK_SAMPLE_COUNT_1_BIT;ii.tiling=fi.tiling;ii.usage=usage;ii.sharingMode=VK_SHARING_MODE_EXCLUSIVE;ii.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;vkcheck(vkCreateImage(device,&ii,nullptr,&vkImage),"create imported image");
  VkImportAndroidHardwareBufferInfoANDROID imp{VK_STRUCTURE_TYPE_IMPORT_ANDROID_HARDWARE_BUFFER_INFO_ANDROID};imp.buffer=ahb;VkMemoryDedicatedAllocateInfo dedicated{VK_STRUCTURE_TYPE_MEMORY_DEDICATED_ALLOCATE_INFO};dedicated.image=vkImage;dedicated.pNext=&imp;
  VkMemoryAllocateInfo ma{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ma.pNext=&dedicated;ma.allocationSize=ap.allocationSize;ma.memoryTypeIndex=type(ap.memoryTypeBits,0);vkcheck(vkAllocateMemory(device,&ma,nullptr,&memory),"import AHB memory");vkcheck(vkBindImageMemory(device,vkImage,memory,0),"bind AHB image");
  const EGLint ia[]={EGL_IMAGE_PRESERVED_KHR,EGL_TRUE,EGL_NONE};image=createImage(display,EGL_NO_CONTEXT,EGL_NATIVE_BUFFER_ANDROID,clientBuffer(ahb),ia);supported(image!=EGL_NO_IMAGE_KHR,"EGLImage native import unavailable");
  glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);imageTarget(GL_TEXTURE_2D,reinterpret_cast<GLeglImageOES>(image));
  glGenFramebuffers(1,&fbo);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);supported(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"import not color renderable");need(glGetError()==GL_NO_ERROR,"GL image setup");
  VkCommandPoolCreateInfo pc{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pc.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;pc.queueFamilyIndex=family;vkcheck(vkCreateCommandPool(device,&pc,nullptr,&pool),"command pool");VkCommandBufferAllocateInfo ac{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};ac.commandPool=pool;ac.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ac.commandBufferCount=1;vkcheck(vkAllocateCommandBuffers(device,&ac,&command),"command buffer");
  VkExportSemaphoreCreateInfo se{VK_STRUCTURE_TYPE_EXPORT_SEMAPHORE_CREATE_INFO};se.handleTypes=VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT;VkSemaphoreCreateInfo sc{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};sc.pNext=&se;vkcheck(vkCreateSemaphore(device,&sc,nullptr,&produced),"export semaphore");sc.pNext=nullptr;vkcheck(vkCreateSemaphore(device,&sc,nullptr,&consumed),"import semaphore");
  VkFenceCreateInfo fc{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};vkcheck(vkCreateFence(device,&fc,nullptr,&completed),"completion fence");
 }
 void barrier(bool acquire,bool initial,VkAccessFlags access){VkImageMemoryBarrier b{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};b.oldLayout=initial?VK_IMAGE_LAYOUT_UNDEFINED:VK_IMAGE_LAYOUT_GENERAL;b.newLayout=VK_IMAGE_LAYOUT_GENERAL;b.srcQueueFamilyIndex=acquire?VK_QUEUE_FAMILY_FOREIGN_EXT:family;b.dstQueueFamilyIndex=acquire?family:VK_QUEUE_FAMILY_FOREIGN_EXT;b.image=vkImage;b.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};b.srcAccessMask=acquire?0:access;b.dstAccessMask=acquire?access:0;vkCmdPipelineBarrier(command,acquire?VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT:VK_PIPELINE_STAGE_TRANSFER_BIT,acquire?VK_PIPELINE_STAGE_TRANSFER_BIT:VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,0,0,nullptr,0,nullptr,1,&b);}
 void begin(){VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;vkcheck(vkBeginCommandBuffer(command,&bi),"begin commands");}
 void run(){
  begin();barrier(true,true,VK_ACCESS_TRANSFER_WRITE_BIT);VkClearColorValue red{{1,0,0,1}};VkImageSubresourceRange range{VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};vkCmdClearColorImage(command,vkImage,VK_IMAGE_LAYOUT_GENERAL,&red,1,&range);barrier(false,false,VK_ACCESS_TRANSFER_WRITE_BIT);vkcheck(vkEndCommandBuffer(command),"end clear");
  VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&command;submit.signalSemaphoreCount=1;submit.pSignalSemaphores=&produced;vkcheck(vkQueueSubmit(queue,1,&submit,completed),"submit Vulkan producer");
  VkSemaphoreGetFdInfoKHR gf{VK_STRUCTURE_TYPE_SEMAPHORE_GET_FD_INFO_KHR};gf.semaphore=produced;gf.handleType=VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT;Fd vkfd;vkcheck(getFd(device,&gf,&vkfd.value),"export Vulkan fence");
  // Vulkan SYNC_FD export -1 is an already-signaled payload, NOT EGL's error convention.
  if(vkfd.value>=0){EGLint sa[]={EGL_SYNC_NATIVE_FENCE_FD_ANDROID,vkfd.take(),EGL_NONE};auto s=createSync(display,EGL_SYNC_NATIVE_FENCE_ANDROID,sa);need(s!=EGL_NO_SYNC_KHR,"EGL native fence import");bool ok=waitSync(display,s,0);destroySync(display,s);need(ok,"EGL server wait");}
  std::array<uint8_t,1024> pixels{};glReadPixels(0,0,16,16,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());for(size_t i=0;i<pixels.size();i+=4)need(pixels[i]==255&&pixels[i+1]==0&&pixels[i+2]==0&&pixels[i+3]==255,"Vulkan to GLES pixel mismatch");
  glClearColor(0,1,0,1);glClear(GL_COLOR_BUFFER_BIT);need(glGetError()==GL_NO_ERROR,"GL producer commands");auto s=createSync(display,EGL_SYNC_NATIVE_FENCE_ANDROID,nullptr);need(s!=EGL_NO_SYNC_KHR,"create GL export fence");glFlush();Fd glfd;glfd.value=duplicate(display,s);destroySync(display,s);need(glfd.value>=0,"EGL export failed (no unsynchronized fallback)");
  VkImportSemaphoreFdInfoKHR im{VK_STRUCTURE_TYPE_IMPORT_SEMAPHORE_FD_INFO_KHR};im.semaphore=consumed;im.flags=VK_SEMAPHORE_IMPORT_TEMPORARY_BIT;im.handleType=VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT;im.fd=glfd.value;vkcheck(importFd(device,&im),"import GL fence");glfd.take();
  vkcheck(vkWaitForFences(device,1,&completed,VK_TRUE,10000000000ULL),"producer completion timeout");vkcheck(vkResetFences(device,1,&completed),"reset fence");vkcheck(vkResetCommandBuffer(command,0),"reset commands");
  VkBufferCreateInfo bc{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bc.size=pixels.size();bc.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT;bc.sharingMode=VK_SHARING_MODE_EXCLUSIVE;vkcheck(vkCreateBuffer(device,&bc,nullptr,&readBuffer),"read buffer");VkMemoryRequirements mr{};vkGetBufferMemoryRequirements(device,readBuffer,&mr);VkMemoryAllocateInfo ma{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ma.allocationSize=mr.size;ma.memoryTypeIndex=type(mr.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);vkcheck(vkAllocateMemory(device,&ma,nullptr,&readMemory),"read memory");vkcheck(vkBindBufferMemory(device,readBuffer,readMemory,0),"read bind");
  begin();barrier(true,false,VK_ACCESS_TRANSFER_READ_BIT);VkBufferImageCopy copy{};copy.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};copy.imageExtent={16,16,1};vkCmdCopyImageToBuffer(command,vkImage,VK_IMAGE_LAYOUT_GENERAL,readBuffer,1,&copy);
  VkBufferMemoryBarrier mb{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};mb.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;mb.dstAccessMask=VK_ACCESS_HOST_READ_BIT;mb.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;mb.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;mb.buffer=readBuffer;mb.size=VK_WHOLE_SIZE;vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&mb,0,nullptr);barrier(false,false,VK_ACCESS_TRANSFER_READ_BIT);vkcheck(vkEndCommandBuffer(command),"end readback");
  VkPipelineStageFlags wait=VK_PIPELINE_STAGE_TRANSFER_BIT;submit.signalSemaphoreCount=0;submit.pSignalSemaphores=nullptr;submit.waitSemaphoreCount=1;submit.pWaitSemaphores=&consumed;submit.pWaitDstStageMask=&wait;vkcheck(vkQueueSubmit(queue,1,&submit,completed),"submit Vulkan consumer");vkcheck(vkWaitForFences(device,1,&completed,VK_TRUE,10000000000ULL),"consumer completion timeout");vkcheck(vkMapMemory(device,readMemory,0,pixels.size(),0,&address),"map readback");mapped=true;auto* p=static_cast<uint8_t*>(address);for(size_t i=0;i<pixels.size();i+=4)need(p[i]==0&&p[i+1]==255&&p[i+2]==0&&p[i+3]==255,"GLES to Vulkan pixel mismatch");
 }
};
}
int main(){try{Lab lab;lab.eglInit();lab.vkInit();lab.allocate();lab.run();std::cout<<"{\"status\":\"PASS\",\"roundtrip_pixels\":512,\"protected\":false,\"performance\":null}\n";return 0;}catch(const Unsupported&e){std::cout<<"{\"status\":\"UNSUPPORTED\",\"reason\":\""<<e.what()<<"\",\"fallback\":\"GLES-only or explicit CPU staging\"}\n";return 77;}catch(const std::exception&e){std::cerr<<"{\"status\":\"FAIL\",\"reason\":\""<<e.what()<<"\"}\n";return 1;}}
