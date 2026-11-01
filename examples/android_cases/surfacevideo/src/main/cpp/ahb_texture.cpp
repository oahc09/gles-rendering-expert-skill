// SPDX-License-Identifier: MIT
// Android API26: CPU-owned RGBA8 producer -> AHB -> EGLImage -> GLES2D texture.
// Intentionally synchronous validation path, not zero-cost/async performance
// advice.
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>

// Extension typedefs require the core GL types above.
#include <GLES2/gl2ext.h>
#include <android/hardware_buffer.h>
#include <android/log.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <jni.h>
#include <memory>
#include <string>

namespace {
thread_local std::string error;
constexpr uint32_t width = 16, height = 16;
struct ImageOwner {
  AHardwareBuffer *buffer =
      nullptr; // Own allocation reference, never borrowed.
  EGLDisplay display =
      EGL_NO_DISPLAY; // Borrowed from GLSurfaceView, do not terminate.
  EGLContext context =
      EGL_NO_CONTEXT; // Borrowed owner identity, do not destroy.
  EGLImageKHR image = EGL_NO_IMAGE_KHR;
  GLuint texture = 0;
  PFNEGLDESTROYIMAGEKHRPROC destroy = nullptr;
  bool locked = false;
  void release(bool currentContextAlive) {
    if (!buffer && image == EGL_NO_IMAGE_KHR && texture == 0 && !locked)
      return;
    if (locked && buffer) {
      AHardwareBuffer_unlock(buffer, nullptr);
      locked = false;
    }
    if (currentContextAlive && context == eglGetCurrentContext() &&
        display == eglGetCurrentDisplay()) {
      // Finish consumers BEFORE releasing owned backing references. Deliberate
      // blocking correctness path.
      glFinish();
      if (texture)
        glDeleteTextures(1, &texture);
    }
    // On actual context recreation: never delete stale GL names in the new
    // context.
    texture = 0;
    if (image != EGL_NO_IMAGE_KHR && destroy) {
      if (!destroy(display, image))
        __android_log_print(ANDROID_LOG_WARN, "GLES-AHB",
                            "eglDestroyImage failed: 0x%x", eglGetError());
      image = EGL_NO_IMAGE_KHR;
    }
    if (buffer) {
      AHardwareBuffer_release(buffer);
      buffer = nullptr;
    }
  }
  ~ImageOwner() { release(true); }
};
bool contains(const char *list, const char *token) {
  if (!list)
    return false;
  const size_t len = std::strlen(token);
  const char *at = list;
  while ((at = std::strstr(at, token))) {
    if ((at == list || at[-1] == ' ') && (at[len] == '\0' || at[len] == ' '))
      return true;
    at += len;
  }
  return false;
}
bool glExtension(const char *token) {
  GLint n = 0;
  glGetIntegerv(GL_NUM_EXTENSIONS, &n);
  for (GLint i = 0; i < n; i++)
    if (std::strcmp(
            reinterpret_cast<const char *>(glGetStringi(GL_EXTENSIONS, i)),
            token) == 0)
      return true;
  return false;
}
ImageOwner *from(jlong value) {
  return reinterpret_cast<ImageOwner *>(static_cast<intptr_t>(value));
}
std::array<uint8_t, 4> pixel(uint32_t x, uint32_t y) {
  return {static_cast<uint8_t>(x < width / 2 ? 255 : 0),
          static_cast<uint8_t>(y < height / 2 ? 255 : 0),
          static_cast<uint8_t>((x >= width / 2 && y >= height / 2) ? 255 : 0),
          255};
}
struct TextureBinding {
  GLint old = 0;
  TextureBinding() { glGetIntegerv(GL_TEXTURE_BINDING_2D, &old); }
  ~TextureBinding() { glBindTexture(GL_TEXTURE_2D, static_cast<GLuint>(old)); }
};
} // namespace
extern "C" JNIEXPORT jlong JNICALL
Java_org_example_gleslab_NativeHardwareBufferDisplay_nativeCreate(JNIEnv *,
                                                                  jclass) {
  error.clear();
  std::unique_ptr<ImageOwner> owner(new ImageOwner());
  owner->display = eglGetCurrentDisplay();
  owner->context = eglGetCurrentContext();
  if (owner->display == EGL_NO_DISPLAY || owner->context == EGL_NO_CONTEXT) {
    error = "No current EGL owner";
    return 0;
  }
  const char *extensions = eglQueryString(owner->display, EGL_EXTENSIONS);
  if (!contains(extensions, "EGL_ANDROID_get_native_client_buffer") ||
      !contains(extensions, "EGL_ANDROID_image_native_buffer") ||
      !contains(extensions, "EGL_KHR_image_base") ||
      !glExtension("GL_OES_EGL_image")) {
    error =
        "Required EGLImage/AHardwareBuffer/GL_OES_EGL_image capability absent";
    return 0;
  }
  auto getBuffer = reinterpret_cast<PFNEGLGETNATIVECLIENTBUFFERANDROIDPROC>(
      eglGetProcAddress("eglGetNativeClientBufferANDROID"));
  auto create = reinterpret_cast<PFNEGLCREATEIMAGEKHRPROC>(
      eglGetProcAddress("eglCreateImageKHR"));
  owner->destroy = reinterpret_cast<PFNEGLDESTROYIMAGEKHRPROC>(
      eglGetProcAddress("eglDestroyImageKHR"));
  auto bindImage = reinterpret_cast<PFNGLEGLIMAGETARGETTEXTURE2DOESPROC>(
      eglGetProcAddress("glEGLImageTargetTexture2DOES"));
  if (!getBuffer || !create || !owner->destroy || !bindImage) {
    error = "Missing EGL/GL entrypoint";
    return 0;
  }
  AHardwareBuffer_Desc desc{};
  desc.width = width;
  desc.height = height;
  desc.layers = 1;
  desc.format = AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM;
  desc.usage = AHARDWAREBUFFER_USAGE_CPU_WRITE_OFTEN |
               AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE |
               AHARDWAREBUFFER_USAGE_GPU_FRAMEBUFFER;
  if (AHardwareBuffer_allocate(&desc, &owner->buffer) != 0 || !owner->buffer) {
    error = "AHardwareBuffer_allocate unsupported format/usage";
    return 0;
  }
  AHardwareBuffer_describe(owner->buffer, &desc);
  void *address = nullptr;
  // Newly allocated, never submitted to GPU: no prior producer fence is needed.
  if (AHardwareBuffer_lock(owner->buffer, AHARDWAREBUFFER_USAGE_CPU_WRITE_OFTEN,
                           -1, nullptr, &address) != 0) {
    error = "AHardwareBuffer_lock failed";
    return 0;
  }
  owner->locked = true;
  if (!address) {
    error = "AHardwareBuffer_lock returned no address";
    return 0;
  }
  if (desc.stride < width) {
    error = "Invalid AHB stride";
    return 0;
  }
  for (uint32_t y = 0; y < height; y++)
    for (uint32_t x = 0; x < width; x++) {
      const auto rgba = pixel(x, y);
      std::memcpy(static_cast<uint8_t *>(address) +
                      (static_cast<size_t>(y) * desc.stride + x) * 4,
                  rgba.data(), 4);
    }
  // nullptr fence requests synchronous completion (official NDK contract).
  const int unlockResult = AHardwareBuffer_unlock(owner->buffer, nullptr);
  owner->locked = false;
  if (unlockResult != 0) {
    error = "AHardwareBuffer_unlock failed; no import";
    return 0;
  }
  EGLClientBuffer client = getBuffer(
      owner->buffer); // Borrowed representation; never free or truncate it.
  if (!client) {
    error = "eglGetNativeClientBufferANDROID failed";
    return 0;
  }
  const EGLint attrs[] = {EGL_IMAGE_PRESERVED_KHR, EGL_TRUE, EGL_NONE};
  owner->image = create(owner->display, EGL_NO_CONTEXT,
                        EGL_NATIVE_BUFFER_ANDROID, client, attrs);
  if (owner->image == EGL_NO_IMAGE_KHR) {
    error = "eglCreateImageKHR native import failed";
    return 0;
  }
  TextureBinding restore;
  glGenTextures(1, &owner->texture);
  glBindTexture(GL_TEXTURE_2D, owner->texture);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
  bindImage(GL_TEXTURE_2D, reinterpret_cast<GLeglImageOES>(owner->image));
  if (glGetError() != GL_NO_ERROR) {
    error = "EGLImage 2D target rejected";
    return 0;
  }
  return static_cast<jlong>(reinterpret_cast<intptr_t>(owner.release()));
}
extern "C" JNIEXPORT jint JNICALL
Java_org_example_gleslab_NativeHardwareBufferDisplay_nativeTexture(
    JNIEnv *, jclass, jlong handle) {
  auto *owner = from(handle);
  return owner ? static_cast<jint>(owner->texture) : 0;
}
extern "C" JNIEXPORT jboolean JNICALL
Java_org_example_gleslab_NativeHardwareBufferDisplay_nativeCheckPattern(
    JNIEnv *, jclass, jlong handle) {
  auto *owner = from(handle);
  if (!owner || owner->context != eglGetCurrentContext() ||
      owner->display != eglGetCurrentDisplay()) {
    error = "Pattern check on wrong EGL owner";
    return JNI_FALSE;
  }
  GLint read = 0, draw = 0;
  glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &read);
  glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &draw);
  GLuint fbo = 0;
  glGenFramebuffers(1, &fbo);
  glBindFramebuffer(GL_FRAMEBUFFER, fbo);
  glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D,
                         owner->texture, 0);
  bool ok = glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE;
  GLint packBuffer = 0, packAlignment = 0, packRow = 0, packSkipRows = 0,
        packSkipPixels = 0;
  glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &packBuffer);
  glGetIntegerv(GL_PACK_ALIGNMENT, &packAlignment);
  glGetIntegerv(GL_PACK_ROW_LENGTH, &packRow);
  glGetIntegerv(GL_PACK_SKIP_ROWS, &packSkipRows);
  glGetIntegerv(GL_PACK_SKIP_PIXELS, &packSkipPixels);
  glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
  glPixelStorei(GL_PACK_ALIGNMENT, 4);
  glPixelStorei(GL_PACK_ROW_LENGTH, 0);
  glPixelStorei(GL_PACK_SKIP_ROWS, 0);
  glPixelStorei(GL_PACK_SKIP_PIXELS, 0);
  std::array<uint8_t, width * height * 4> actual{};
  if (ok) {
    glReadBuffer(GL_COLOR_ATTACHMENT0);
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, actual.data());
    ok = glGetError() == GL_NO_ERROR;
  }
  if (ok)
    for (uint32_t y = 0; y < height; y++)
      for (uint32_t x = 0; x < width; x++) {
        auto expected = pixel(x, y);
        if (std::memcmp(actual.data() + (y * width + x) * 4, expected.data(),
                        4) != 0)
          ok = false;
      }
  glBindBuffer(GL_PIXEL_PACK_BUFFER, static_cast<GLuint>(packBuffer));
  glPixelStorei(GL_PACK_ALIGNMENT, packAlignment);
  glPixelStorei(GL_PACK_ROW_LENGTH, packRow);
  glPixelStorei(GL_PACK_SKIP_ROWS, packSkipRows);
  glPixelStorei(GL_PACK_SKIP_PIXELS, packSkipPixels);
  glBindFramebuffer(GL_READ_FRAMEBUFFER, static_cast<GLuint>(read));
  glBindFramebuffer(GL_DRAW_FRAMEBUFFER, static_cast<GLuint>(draw));
  glDeleteFramebuffers(1, &fbo);
  if (!ok)
    error = "AHB import/FBO/readback pattern mismatch; native path rejected";
  return ok ? JNI_TRUE : JNI_FALSE;
}
extern "C" JNIEXPORT void JNICALL
Java_org_example_gleslab_NativeHardwareBufferDisplay_nativeRelease(
    JNIEnv *, jclass, jlong handle, jboolean ownerAlive) {
  auto *owner = from(handle);
  if (!owner)
    return;
  owner->release(ownerAlive == JNI_TRUE);
  delete owner;
}
extern "C" JNIEXPORT jstring JNICALL
Java_org_example_gleslab_NativeHardwareBufferDisplay_nativeError(JNIEnv *env,
                                                                 jclass) {
  return env->NewStringUTF(error.c_str());
}
