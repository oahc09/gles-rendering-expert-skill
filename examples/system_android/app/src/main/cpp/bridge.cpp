// SPDX-License-Identifier: MIT
#include "../../../../multi_surface.hpp"
#include <android/native_window_jni.h>
#include <jni.h>
#include <memory>
namespace {
std::mutex registryMutex;std::map<jlong,std::shared_ptr<MultiSurface>> labRegistry;jlong sequence=1;
std::shared_ptr<MultiSurface> get(jlong key){std::lock_guard<std::mutex>l(registryMutex);auto i=labRegistry.find(key);return i==labRegistry.end()?nullptr:i->second;}
void fail(JNIEnv*env,const char*text){env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),text);}
}
extern "C" JNIEXPORT jlong JNICALL Java_org_example_systemlab_MultiSurfaceActivity_create(JNIEnv*env,jclass){try{auto lab=std::make_shared<MultiSurface>();std::lock_guard<std::mutex>l(registryMutex);jlong id=sequence++;labRegistry[id]=lab;return id;}catch(const std::exception&e){fail(env,e.what());return 0;}}
extern "C" JNIEXPORT jlong JNICALL Java_org_example_systemlab_MultiSurfaceActivity_attach(JNIEnv*env,jclass,jlong id,jobject surface){auto lab=get(id);if(!lab)return 0;ANativeWindow*w=ANativeWindow_fromSurface(env,surface);if(!w)return 0;try{auto key=lab->window(w);ANativeWindow_release(w);return static_cast<jlong>(key);}catch(const std::exception&e){ANativeWindow_release(w);fail(env,e.what());return 0;}}
extern "C" JNIEXPORT void JNICALL Java_org_example_systemlab_MultiSurfaceActivity_detach(JNIEnv*,jclass,jlong id,jlong key){auto lab=get(id);if(lab)lab->remove(static_cast<uint64_t>(key));}
extern "C" JNIEXPORT jboolean JNICALL Java_org_example_systemlab_MultiSurfaceActivity_draw(JNIEnv*env,jclass,jlong id,jlong key){auto lab=get(id);if(!lab)return JNI_FALSE;try{return lab->render(static_cast<uint64_t>(key))?JNI_TRUE:JNI_FALSE;}catch(const std::exception&e){fail(env,e.what());return JNI_FALSE;}}
extern "C" JNIEXPORT void JNICALL Java_org_example_systemlab_MultiSurfaceActivity_rebuild(JNIEnv*env,jclass,jlong id){auto lab=get(id);if(!lab)return;try{lab->forceRebuild();}catch(const std::exception&e){fail(env,e.what());}}
extern "C" JNIEXPORT void JNICALL Java_org_example_systemlab_MultiSurfaceActivity_destroy(JNIEnv*,jclass,jlong id){std::shared_ptr<MultiSurface> old;{std::lock_guard<std::mutex>l(registryMutex);auto i=labRegistry.find(id);if(i!=labRegistry.end()){old=std::move(i->second);labRegistry.erase(i);}}}
