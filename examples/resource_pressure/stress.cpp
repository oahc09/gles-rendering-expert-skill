// SPDX-License-Identifier: MIT
// Reuse the established EGL lifecycle/capability implementation without cloning it.
#define main predecessor_validation_main
#include "../validation/egl_smoke.cpp"
#undef main
#include "completion_policy.hpp"
#include <chrono>
#include <list>
#include <memory>
#include <numeric>
#include <vector>

namespace pressure {
enum Kind { Texture, Buffer, Fence, Framebuffer, KindCount };
struct Accounting {
    std::array<unsigned,KindCount> created{},deleted{},live{},peak{};
    unsigned generation=1, evictions=0, budgetRejects=0, lowMemorySignals=0;
    unsigned zeroTimeoutPending=0, zeroTimeoutComplete=0, canceledTransfers=0;
    unsigned uploadTransfers=0, readTransfers=0, completedTransfers=0;
    size_t estimatedBytes=0, peakEstimatedBytes=0;
    void add(Kind k) { ++created[k]; ++live[k]; peak[k]=std::max(peak[k],live[k]); }
    void remove(Kind k) { require(live[k]>0,"object count underflow"); --live[k]; ++deleted[k]; }
    unsigned total() const { return std::accumulate(live.begin(),live.end(),0U); }
};
struct TextureEntry {
    GLuint name=0; unsigned key=0; bool pinned=false; size_t bytes=0; unsigned long stamp=0;
};
class TextureBudget {
    Accounting& stats; Owner owner; size_t budget; unsigned long clock=0;
    std::list<TextureEntry> entries;
    void erase(std::list<TextureEntry>::iterator it) {
        glDeleteTextures(1,&it->name); require(glIsTexture(it->name)==GL_FALSE,"deleted texture still a live name"); stats.remove(Texture); stats.estimatedBytes-=it->bytes; entries.erase(it);
    }
public:
    TextureBudget(Accounting& s,size_t limit):stats(s),owner{std::this_thread::get_id(),s.generation},budget(limit) {}
    TextureBudget(const TextureBudget&)=delete;
    TextureBudget& operator=(const TextureBudget&)=delete;
    ~TextureBudget() { clear(); }
    GLuint get(unsigned key,bool pin=false) {
        owner.check(stats.generation);
        for(auto& entry:entries) if(entry.key==key) { entry.stamp=++clock; return entry.name; }
        constexpr size_t bytes=16*16*4; // Base-level RGBA8 engine allocation estimate, NOT VRAM residency.
        while(stats.estimatedBytes+bytes>budget) {
            auto victim=entries.end();
            for(auto it=entries.begin();it!=entries.end();++it)
                if(!it->pinned && (victim==entries.end() || it->stamp<victim->stamp)) victim=it;
            if(victim==entries.end()) { ++stats.budgetRejects; return 0; }
            erase(victim); ++stats.evictions;
        }
        TextureEntry entry; entry.key=key; entry.pinned=pin; entry.bytes=bytes; entry.stamp=++clock;
        glGenTextures(1,&entry.name); require(entry.name!=0,"texture allocation");
        glBindTexture(GL_TEXTURE_2D,entry.name); glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,16,16);
        gl_ok("texture storage"); entries.push_back(entry); stats.add(Texture);
        stats.estimatedBytes+=bytes; stats.peakEstimatedBytes=std::max(stats.peakEstimatedBytes,stats.estimatedBytes);
        return entry.name;
    }
    bool contains(unsigned key) const { for(const auto& e:entries) if(e.key==key) return true; return false; }
    void low_memory() {
        owner.check(stats.generation); ++stats.lowMemorySignals;
        for(auto it=entries.begin();it!=entries.end();) {
            if(it->pinned) { ++it; continue; }
            auto victim=it++; erase(victim); ++stats.evictions;
        }
    }
    void clear() {
        owner.check(stats.generation);
        while(!entries.empty()) erase(entries.begin());
    }
};
class Transfer {
    Accounting& stats; Owner owner; GLuint buffer=0; GLsync fence=nullptr;
    CompletionPolicy policy; bool reading=false;
public:
    Transfer(Accounting& s,GLuint texture,bool read,const std::array<GLubyte,4>& expected)
        :stats(s),owner{std::this_thread::get_id(),s.generation},reading(read) {
        glGenBuffers(1,&buffer); require(buffer!=0,"PBO allocation"); stats.add(Buffer);
        const GLenum target=read?GL_PIXEL_PACK_BUFFER:GL_PIXEL_UNPACK_BUFFER;
        glBindBuffer(target,buffer); glBufferData(target,4,read?nullptr:expected.data(),GL_STREAM_DRAW);
        if(read) { glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,nullptr); ++stats.readTransfers; }
        else {
            glBindTexture(GL_TEXTURE_2D,texture);
            glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,nullptr); ++stats.uploadTransfers;
        }
        glBindBuffer(target,0); gl_ok("PBO transfer command");
        fence=glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE,0); require(fence!=nullptr,"transfer fence");
        stats.add(Fence); glFlush();
    }
    Transfer(const Transfer&)=delete;
    Transfer& operator=(const Transfer&)=delete;
    ~Transfer() {
        // Error cleanup may delete GL names still referenced by queued commands: GL retains
        // underlying objects as required. No slot is recycled or exposed by this destructor.
        owner.check(stats.generation);
        if(fence) { glDeleteSync(fence); stats.remove(Fence); }
        if(buffer) { glDeleteBuffers(1,&buffer); require(glIsBuffer(buffer)==GL_FALSE,"deleted PBO still live"); stats.remove(Buffer); }
    }
    void cancel() { owner.check(stats.generation); if(!policy.canceled) ++stats.canceledTransfers; policy.cancel(); }
    bool poll(GLuint64 timeout=0) {
        owner.check(stats.generation);
        GLenum result=glClientWaitSync(fence,0,timeout);
        if(result==GL_ALREADY_SIGNALED || result==GL_CONDITION_SATISFIED) {
            if(timeout==0) ++stats.zeroTimeoutComplete;
            if(!policy.completed) ++stats.completedTransfers;
            policy.observe(Completion::Complete);
        } else if(result==GL_TIMEOUT_EXPIRED) {
            if(timeout==0) ++stats.zeroTimeoutPending;
            policy.observe(Completion::Pending);
        } else { policy.observe(Completion::Failed); throw std::runtime_error("GL_WAIT_FAILED: no reuse"); }
        return policy.can_recycle();
    }
    void finish(const std::array<GLubyte,4>& expected) {
        bool ready=poll();
        for(unsigned i=0;i<100 && !ready;++i) ready=poll(10000000ULL);
        require(ready,"bounded fence timeout: do not reuse");
        if(reading && policy.can_consume()) {
            glBindBuffer(GL_PIXEL_PACK_BUFFER,buffer);
            auto* pixel=static_cast<GLubyte*>(glMapBufferRange(GL_PIXEL_PACK_BUFFER,0,4,GL_MAP_READ_BIT));
            require(pixel!=nullptr,"read PBO map");
            const bool equal=std::equal(expected.begin(),expected.end(),pixel);
            require(glUnmapBuffer(GL_PIXEL_PACK_BUFFER)==GL_TRUE,"read PBO unmap corruption");
            glBindBuffer(GL_PIXEL_PACK_BUFFER,0); require(equal,"read PBO pixel differs");
        }
        require(!policy.canceled || !policy.can_consume(),"canceled results exposed"); gl_ok("transfer finish");
    }
};
struct Fbo {
    Accounting& stats; GLuint name=0;
    explicit Fbo(Accounting& s,GLuint texture):stats(s) {
        glGenFramebuffers(1,&name); stats.add(Framebuffer); glBindFramebuffer(GL_FRAMEBUFFER,name);
        glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
        require(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE,"stress FBO complete");
        glReadBuffer(GL_COLOR_ATTACHMENT0);
    }
    ~Fbo() { glBindFramebuffer(GL_FRAMEBUFFER,0); glDeleteFramebuffers(1,&name); require(glIsFramebuffer(name)==GL_FALSE,"deleted FBO still live"); stats.remove(Framebuffer); }
    Fbo(const Fbo&)=delete;
};
static void policy_tests() {
    // These are deliberately synthetic completion statuses, not a claim the GPU was delayed.
    CompletionPolicy canceled; canceled.cancel(); canceled.observe(Completion::Pending);
    require(!canceled.can_recycle() && !canceled.can_consume(),"cancel must retain pending slot");
    canceled.observe(Completion::Complete);
    require(canceled.can_recycle() && !canceled.can_consume(),"cancel retires only after complete");
    CompletionPolicy queued; queued.observe(Completion::Pending);
    require(!queued.can_consume() && !queued.can_recycle(),"pending slot exposed");
    queued.observe(Completion::Complete); require(queued.can_consume(),"complete slot not consumable");
    CompletionPolicy failed; failed.observe(Completion::Failed); failed.observe(Completion::Complete);
    require(!failed.can_recycle(),"failed wait must remain fail-closed");
    Owner owner{std::this_thread::get_id(),1}; bool staleRejected=false;
    try { owner.check(2); } catch(const std::logic_error&) { staleRejected=true; }
    require(staleRejected,"stale generation accepted");
    bool wrongThreadRejected=false; std::thread other([&] {
        try { owner.check(1); } catch(const std::logic_error&) { wrongThreadRejected=true; }
    }); other.join(); require(wrongThreadRejected,"wrong-thread ownership accepted");
    std::cout<<"{\"case\":\"synthetic-completion-policy\",\"status\":\"PASS\",\"real_gpu_delayed_completion\":false,\"assertions\":7}\n";
}
static void scene(Accounting& stats,unsigned index) {
    constexpr size_t limit=8*1024;
    TextureBudget cache(stats,limit);
    GLuint primary=cache.get(0,true); require(primary!=0,"pinned texture");
    require(cache.get(1)!=0 && cache.get(2)!=0,"cache seed");
    cache.get(1); // Explicit LRU refresh before burst.
    for(unsigned k=3;k<8;++k) require(cache.get(k)!=0,"budgeted burst fill");
    require(cache.get(8)!=0 && cache.contains(1) && !cache.contains(2),"LRU touch order violated");
    for(unsigned k=9;k<18;++k) require(cache.get(k)!=0,"budgeted burst eviction");
    require(cache.contains(0) && !cache.contains(1),"pinned survival and old LRU eviction");
    require(stats.estimatedBytes<=limit,"estimated texture budget exceeded");
    {
        Fbo framebuffer(stats,primary);
        std::vector<std::unique_ptr<Transfer>> burst;
        for(unsigned j=0;j<8;++j) {
            std::array<GLubyte,4> value{static_cast<GLubyte>(index),static_cast<GLubyte>(j),127,255};
            burst.emplace_back(std::make_unique<Transfer>(stats,primary,false,value));
            if(j%3==0) burst.back()->cancel(); // Cancellation suppresses publication, not GPU execution.
        }
        std::array<GLubyte,4> final{static_cast<GLubyte>(index),7,127,255};
        for(auto& transfer:burst) transfer->finish(final);
        burst.clear();
        for(unsigned j=0;j<4;++j) {
            Transfer read(stats,primary,true,final);
            if(j==0) read.cancel();
            read.finish(final);
        }
        read_pixel(final); // Independent direct read confirms the final upload even on canceled result paths.
    }
    cache.low_memory(); require(cache.contains(0) && stats.estimatedBytes==1024,"low-memory pinned tier");
    cache.clear(); require(stats.estimatedBytes==0 && stats.total()==0,"scene cleanup leaked owned objects");
    // A fully pinned budget must reject instead of evicting essential resources or exceeding the budget.
    { TextureBudget pinned(stats,1024); require(pinned.get(1,true)!=0,"pinned budget seed");
      require(pinned.get(2)==0,"pinned budget overcommit accepted"); }
    gl_ok("scene cleanup"); require(stats.total()==0,"end scene object growth");
    std::cout<<"{\"scene\":"<<index<<",\"context_generation\":"<<stats.generation
        <<",\"live_owned_objects\":"<<stats.total()<<",\"engine_estimated_texture_bytes\":"<<stats.estimatedBytes<<"}\n";
}
}
int main(int argc,char** argv) {
    try {
        const unsigned scenes=argc>1?static_cast<unsigned>(std::stoul(argv[1])):100;
        require(scenes>=100 && scenes<=10000,"scene count must be 100..10000");
        EGLSession session; session.open(); snapshot(session); pressure::Accounting stats;
        pressure::policy_tests(); unsigned surfaceRebuilds=0,contextRebuilds=0;
        for(unsigned i=0;i<scenes;++i) {
            pressure::scene(stats,i);
            if((i+1)%10==0) {
                require(stats.total()==0,"surface reset has live app resources"); session.release();
                require(eglDestroySurface(session.display,session.surface),"destroy pbuffer"); session.surface=EGL_NO_SURFACE;
                session.surface=session.make_surface(8+(i%3)); session.current(); ++surfaceRebuilds;
            }
            if((i+1)%25==0) {
                require(stats.total()==0,"context reset has live app resources"); session.release();
                require(eglDestroyContext(session.display,session.context),"destroy controlled context"); session.context=EGL_NO_CONTEXT;
                session.context=session.make_context(); session.current(); ++stats.generation; ++contextRebuilds;
                // Recreate and validate a GPU object from retained CPU data in every new generation.
                GLuint rebuilt=0; const std::array<GLubyte,4> cpuPixel{31,63,127,255};
                glGenTextures(1,&rebuilt); glBindTexture(GL_TEXTURE_2D,rebuilt);
                glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,cpuPixel.data());
                stats.add(pressure::Texture);
                { pressure::Fbo check(stats,rebuilt); read_pixel(cpuPixel); }
                glDeleteTextures(1,&rebuilt); stats.remove(pressure::Texture);
                require(stats.total()==0,"recovery check retained app objects");
            }
        }
        for(unsigned k=0;k<pressure::KindCount;++k) require(stats.created[k]==stats.deleted[k],"created/deleted mismatch");
        std::cout<<"{\"summary\":{\"status\":\"PASS\",\"scenes\":"<<scenes
          <<",\"surface_recreates\":"<<surfaceRebuilds<<",\"controlled_context_recreates\":"<<contextRebuilds
          <<",\"context_generation\":"<<stats.generation<<",\"live_owned_objects\":"<<stats.total()
          <<",\"engine_estimated_texture_peak_bytes\":"<<stats.peakEstimatedBytes
          <<",\"evictions\":"<<stats.evictions<<",\"budget_rejections\":"<<stats.budgetRejects
          <<",\"low_memory_signals_simulated\":"<<stats.lowMemorySignals
          <<",\"upload_transfers\":"<<stats.uploadTransfers<<",\"readback_transfers\":"<<stats.readTransfers
          <<",\"canceled_transfers\":"<<stats.canceledTransfers<<",\"completed_transfers\":"<<stats.completedTransfers
          <<",\"actual_zero_timeout_pending\":"<<stats.zeroTimeoutPending<<",\"actual_zero_timeout_complete\":"<<stats.zeroTimeoutComplete
          <<",\"object_counters\":[";
        for(unsigned k=0;k<pressure::KindCount;++k) { if(k)std::cout<<',';
            std::cout<<"{\"kind\":"<<k<<",\"created\":"<<stats.created[k]<<",\"deleted\":"<<stats.deleted[k]<<",\"peak_live\":"<<stats.peak[k]<<"}"; }
        std::cout<<"],\"vram_residency_measurement\":\"NOT_AVAILABLE\",\"driver_internal_leak_check\":\"NOT_MEASURED\",\"android_real_loss\":\"NOT_RUN_DEVICE\",\"AHB_external_runtime\":\"NOT_RUN_DEVICE\"}}\n";
        return 0;
    } catch(const std::exception& error) { std::cerr<<"resource stress FAIL: "<<error.what()<<'\n';return 1; }
}
