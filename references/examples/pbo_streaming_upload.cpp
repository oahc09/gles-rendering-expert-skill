/**
 * @file pbo_streaming_upload.cpp
 * @brief Hitch-free texture streaming with triple-buffered PBOs
 *        (GL_PIXEL_UNPACK_BUFFER) + fence synchronization.
 *
 * Scenario: Large textures updated continuously (video tiles, streamed map
 *           chunks, runtime-generated atlases). A synchronous glTexSubImage2D
 *           from CPU memory stalls the pipeline when the GPU is still reading
 *           the texture; the PBO path lets the DMA/copy engine move data
 *           asynchronously while the CPU fills the next buffer.
 *
 * Target:   OpenGL ES 3.0+ / C++17
 *
 * Rules reference:
 *   - references/rules/gles-api-standards.md §4.3 (buffer mapping), §6 (sync)
 *   - references/rules/mali-arm-best-practices.md (Terrain sample: async PBO upload)
 *
 * Pattern (N-buffered ring, N=3):
 *   Frame F writes into PBO[F % 3] (mapped pointer, CPU side)
 *   Frame F issues glTexSubImage2D from PBO[(F-1) % 3]  (already filled, GPU waits via fence)
 *   Fence on the upload; the slot is not re-mapped until the fence signals.
 */

#include <GLES3/gl3.h>
#include <cstdio>
#include <cstring>
#include <array>
#include <utility>

#define LOGI(...) printf("[INFO] " __VA_ARGS__), printf("\n")
#define LOGE(...) printf("[ERROR] " __VA_ARGS__), printf("\n")

// ============================================================================
// RAII Buffer
// ============================================================================
class GlBuffer {
public:
    ~GlBuffer() { if (id_ != 0) glDeleteBuffers(1, &id_); }
    GlBuffer(const GlBuffer&) = delete;
    GlBuffer& operator=(const GlBuffer&) = delete;
    GlBuffer(GlBuffer&& o) noexcept : id_(o.id_) { o.id_ = 0; }

    void Create() { glGenBuffers(1, &id_); }
    void Bind(GLenum target) const { glBindBuffer(target, id_); }
    GLuint Id() const { return id_; }
private:
    GLuint id_ = 0;
};

class GlSync {
public:
    ~GlSync() { Reset(); }
    GlSync(const GlSync&) = delete;
    GlSync& operator=(const GlSync&) = delete;

    void Set(GLsync s) { Reset(); sync_ = s; }
    bool IsSignaled(GLuint64 timeoutNs = 0) {
        if (sync_ == nullptr) return true;
        GLenum r = glClientWaitSync(sync_, timeoutNs > 0 ? GL_SYNC_FLUSH_COMMANDS_BIT : 0,
                                    timeoutNs);
        return r == GL_ALREADY_SIGNALED || r == GL_CONDITION_SATISFIED;
    }
    void Reset() {
        if (sync_ != nullptr) { glDeleteSync(sync_); sync_ = nullptr; }
    }
private:
    GLsync sync_ = nullptr;
};

// ============================================================================
// PBO Streaming Uploader (triple-buffered ring)
// ============================================================================
class PboStreamingUploader {
public:
    static constexpr int kSlots = 3;

    /// slotBytes: size of one texture slice uploaded per frame
    bool Init(GLsizeiptr slotBytes) {
        slotBytes_ = slotBytes;
        for (int i = 0; i < kSlots; ++i) {
            pbos_[i].Create();
            pbos_[i].Bind(GL_PIXEL_UNPACK_BUFFER);
            // GL_STREAM_DRAW: content written once, consumed once — matches
            // the streaming pattern and lets the driver pick DMA-friendly memory.
            glBufferData(GL_PIXEL_UNPACK_BUFFER, slotBytes, nullptr, GL_STREAM_DRAW);
        }
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0);
        writeIndex_ = 0;
        primed_ = false;
        LOGI("PBO streaming uploader: %d slots x %lld bytes",
             kSlots, static_cast<long long>(slotBytes));
        return true;
    }

    /// CPU-side: obtain a writable pointer for THIS frame's data.
    /// Blocks only if the slot's upload fence from 3 frames ago has not
    /// signaled (rare at 3 slots). Returns nullptr on failure.
    void* MapWriteSlot() {
        // Wait (bounded) for the slot's previous consumer fence
        if (!fences_[writeIndex_].IsSignaled(10'000'000 /* 10 ms */)) {
            LOGE("PBO slot %d still busy after 10ms — consider more slots", writeIndex_);
            return nullptr;
        }
        fences_[writeIndex_].Reset();

        pbos_[writeIndex_].Bind(GL_PIXEL_UNPACK_BUFFER);
        // INVALIDATE_BUFFER: orphan previous content, avoids implicit sync
        void* ptr = glMapBufferRange(GL_PIXEL_UNPACK_BUFFER, 0, slotBytes_,
                                     GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT |
                                     GL_MAP_UNSYNCHRONIZED_BIT);
        // NOTE: keep the buffer bound; glTexSubImage2D below reads from it.
        return ptr;
    }

    /// GPU-side: enqueue the upload of the slot written LAST frame into a
    /// region of dstTexture, then set a fence protecting the slot.
    ///
    /// The one-frame delay between MapWriteSlot and CommitUpload is what makes
    /// the transfer asynchronous: the CPU never touches data the GPU may be
    /// copying right now.
    void CommitUpload(GLuint dstTexture, GLint x, GLint y,
                      GLsizei w, GLsizei h, GLenum format, GLenum type) {
        // First frame has no previously-filled slot: just advance the ring.
        if (!primed_) {
            primed_ = true;
            writeIndex_ = (writeIndex_ + 1) % kSlots;
            return;
        }
        const int slot = PrevSlot();  // slot filled on the previous frame
        pbos_[slot].Bind(GL_PIXEL_UNPACK_BUFFER);

        glBindTexture(GL_TEXTURE_2D, dstTexture);
        // 'data' is a BYTE OFFSET into the bound PIXEL_UNPACK_BUFFER, not a pointer
        glTexSubImage2D(GL_TEXTURE_2D, 0, x, y, w, h, format, type, nullptr);
        glBindTexture(GL_TEXTURE_2D, 0);

        // Fence: this slot may not be re-mapped until the copy completes
        fences_[slot].Set(glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0));

        glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER);
        glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0);

        writeIndex_ = (writeIndex_ + 1) % kSlots;
        glFlush();  // let the copy engine start without waiting
    }

private:
    int PrevSlot() const { return (writeIndex_ + kSlots - 1) % kSlots; }

    std::array<GlBuffer, kSlots> pbos_;
    std::array<GlSync, kSlots> fences_;
    GLsizeiptr slotBytes_ = 0;
    int writeIndex_ = 0;
    bool primed_ = false;
};

// ============================================================================
// Usage sketch (per-frame streaming of one 1024x1024 RGBA tile):
//
//   PboStreamingUploader up;
//   up.Init(1024 * 1024 * 4);
//
//   // Frame F:
//   void* dst = up.MapWriteSlot();          // CPU writes this frame's tile
//   if (dst) { DecodeTileInto(dst); }
//   up.CommitUpload(tileTexture, tileX, tileY, 1024, 1024,
//                   GL_RGBA, GL_UNSIGNED_BYTE);   // uploads PREVIOUS frame's slot
//
// Anti-patterns avoided:
//   - glTexSubImage2D directly from CPU pointer every frame (pipeline stall)
//   - Single PBO ping-pong (GPU may still be reading when re-mapped)
//   - glFinish() to "be safe" (kills CPU/GPU overlap entirely)
// ============================================================================

int main() {
    LOGI("pbo_streaming_upload: reference implementation — see header comments");
    return 0;
}
