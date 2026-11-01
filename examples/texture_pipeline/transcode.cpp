// MIT original example. libktx is an external Apache-2.0 dependency, not vendored.
#include <ktx.h>
#include <chrono>
#include <fstream>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
static void check(KTX_error_code result) { if(result!=KTX_SUCCESS) throw std::runtime_error(ktxErrorString(result)); }
struct Destroy { void operator()(ktxTexture2* t) const { if(t) ktxTexture_Destroy(ktxTexture(t)); } };
int main(int argc,char**argv) {
 try {
  if(argc!=4) throw std::runtime_error("input.ktx2 astc|etc2|rgba output-prefix; target must come from verified GL capabilities");
  std::string target=argv[2],prefix=argv[3];
  auto format=target=="astc"?KTX_TTF_ASTC_4x4_RGBA:target=="etc2"?KTX_TTF_ETC2_RGBA:KTX_TTF_RGBA32;
  if(target!="astc"&&target!="etc2"&&target!="rgba")throw std::runtime_error("Unknown target");
  auto start=std::chrono::steady_clock::now();
  if(std::filesystem::file_size(argv[1])>16u*1024u*1024u)throw std::runtime_error("Input exceeds 16MiB example budget");
  ktxTexture2* raw=nullptr;check(ktxTexture2_CreateFromNamedFile(argv[1],KTX_TEXTURE_CREATE_NO_FLAGS,&raw));
  std::unique_ptr<ktxTexture2,Destroy> texture(raw);
  if(raw->numDimensions!=2||raw->numLayers!=1||raw->numFaces!=1||raw->numLevels!=1||raw->isArray||raw->baseDepth!=1||raw->baseWidth==0||raw->baseHeight==0||raw->baseWidth>2048||raw->baseHeight>2048)
   throw std::runtime_error("Example accepts one 2D image, one mip; unsupported topology rejected");
  if(!ktxTexture2_NeedsTranscoding(raw))throw std::runtime_error("Requires Basis KTX2 input; precompressed formats need a separate capability check");
  const auto model=ktxTexture2_GetColorModel_e(raw);
  const auto transfer=ktxTexture2_GetTransferFunction_e(raw);
  const auto components=ktxTexture2_GetNumComponents(raw);
  if((model!=KHR_DF_MODEL_UASTC)||
     (transfer!=KHR_DF_TRANSFER_LINEAR&&transfer!=KHR_DF_TRANSFER_SRGB)||
     (components!=3&&components!=4)||raw->vkFormat!=0)
   throw std::runtime_error("Only LDR RGB/RGBA UASTC with linear/sRGB DFD is supported; reject HDR/other components");
  const bool srgb=transfer==KHR_DF_TRANSFER_SRGB;
  check(ktxTexture2_LoadImageData(raw,nullptr,0));
  auto loaded=std::chrono::steady_clock::now();
  check(ktxTexture2_TranscodeBasis(raw,format,0));
  auto done=std::chrono::steady_clock::now();
  auto bytes=ktxTexture_GetDataSize(ktxTexture(raw));
  // VkFormat values from Khronos Vulkan-Headers; validate the actual output, not
  // an assumed four-byte pixel interpretation of an arbitrary transcode result.
  const ktx_uint32_t expected=target=="astc"?(srgb?158u:157u):target=="etc2"?(srgb?152u:151u):(srgb?43u:37u);
  const ktx_size_t rgbaBytes=ktx_size_t(raw->baseWidth)*ktx_size_t(raw->baseHeight)*4u;
  const ktx_size_t expectedBytes=target=="rgba"?rgbaBytes:ktx_size_t((raw->baseWidth+3)/4)*((raw->baseHeight+3)/4)*16u;
  if(raw->vkFormat!=expected||bytes!=expectedBytes||!ktxTexture_GetData(ktxTexture(raw)))
   throw std::runtime_error("Transcoded format/data length mismatch");
  check(ktxTexture2_WriteToNamedFile(raw,(prefix+".ktx2").c_str()));
  // Decode ASTC via official libktx for CPU quality evidence; ETC2 quality needs GPU/decoder.
  if(target=="astc")check(ktxTexture2_DecodeAstc(raw));
  if(target!="etc2") {
   ktx_size_t offset=0;check(ktxTexture2_GetImageOffset(raw,0,0,0,&offset));
   ktx_uint32_t channels=0,componentBytes=0;ktxTexture2_GetComponentInfo(raw,&channels,&componentBytes);
   const ktx_size_t total=ktxTexture_GetDataSize(ktxTexture(raw));
   if(raw->vkFormat!=(srgb?43u:37u)||channels!=4||componentBytes!=1||offset>total||rgbaBytes!=total-offset)
    throw std::runtime_error("Decoded image is not exact tightly packed 8bit RGBA");
   std::ofstream file(prefix+".rgba",std::ios::binary);
   file.write(reinterpret_cast<const char*>(ktxTexture_GetData(ktxTexture(raw))+offset),static_cast<std::streamsize>(rgbaBytes));
   if(!file)throw std::runtime_error("Raw output failed");
  }
  rusage usage{};if(getrusage(RUSAGE_SELF,&usage))throw std::runtime_error("getrusage failed");
  std::cout<<"{\"status\":\"TRANSCODED\",\"target\":\""<<target<<"\",\"width\":"<<raw->baseWidth<<",\"height\":"<<raw->baseHeight
   <<",\"payload_bytes\":"<<bytes<<",\"load_ms\":"<<std::chrono::duration<double,std::milli>(loaded-start).count()
   <<",\"transcode_ms\":"<<std::chrono::duration<double,std::milli>(done-loaded).count()<<",\"process_peak_rss_kib\":"<<usage.ru_maxrss
   <<",\"gpu_upload\":\"NOT_RUN\",\"physical_device\":\"NOT_RUN\"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}
}
