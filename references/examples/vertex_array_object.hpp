/**
 * @file vertex_array_object.hpp
 * @brief RAII-wrapped VBO & VAO with state caching for OpenGL ES 3.0+.
 *
 * Features:
 * - Full RAII lifecycle (no leaked GL handles)
 * - Move semantics (no accidental copies)
 * - State cache to avoid redundant glBind* calls
 * - Buffer orphaning for dynamic updates (TBDR-friendly: avoids sync stalls)
 *
 * Target: OpenGL ES 3.0+ / C++17
 */

#pragma once

#include <GLES3/gl31.h>
#include <utility>
#include <vector>
#include <cstdint>
#include <cassert>
#include <cstdio>

// ============================================================================
// GL State Cache — Avoids redundant driver calls
//
// THREADING MODEL:
//   Each thread that calls eglMakeCurrent owns an independent EGL context and
//   therefore independent GL state. The cache is declared thread_local so that
//   multiple threads sharing GL objects (via shared contexts) never race on
//   cache data. Call Invalidate() immediately after eglMakeCurrent to reset
//   assumptions for the newly bound context.
//
// RESOURCE DELETION:
//   When a GL object is deleted, its name may be reused by a later glGen*.
//   Callers MUST call the corresponding Notify* method (e.g. NotifyBufferDeleted)
//   so the cache does not hold stale entries that would suppress future binds.
//
// UNKNOWN TARGETS:
//   Buffer targets not explicitly listed are NOT cached — the driver call is
//   always issued and the overhead of an extra glBindBuffer is negligible
//   compared to the risk of incorrect caching.
// ============================================================================
class GLStateCache {
public:
    static constexpr GLuint kMaxTextureUnits = 32;
    /// Sentinel indicating unknown state — forces the next call through to the driver.
    static constexpr GLuint kUnknown = ~GLuint(0);

    /// Returns the cache for the current thread (one per EGL context).
    static GLStateCache& Instance() {
        thread_local GLStateCache instance;
        return instance;
    }

    // ----- Bind operations -----

    void BindVertexArray(GLuint vao) {
        if (vao != boundVAO_) {
            glBindVertexArray(vao);
            boundVAO_ = vao;
            // VAO switch implicitly changes the EBO binding.
            boundEBO_ = kUnknown;
        }
    }

    void BindBuffer(GLenum target, GLuint buffer) {
        // EBO binding is VAO state — cache it separately.
        if (target == GL_ELEMENT_ARRAY_BUFFER) {
            if (buffer != boundEBO_) {
                glBindBuffer(target, buffer);
                boundEBO_ = buffer;
            }
            return;
        }
        GLuint* slot = GetBufferSlot(target);
        if (!slot) {
            // Unknown target — always issue the driver call, don’t cache.
            glBindBuffer(target, buffer);
            return;
        }
        if (buffer != *slot) {
            glBindBuffer(target, buffer);
            *slot = buffer;
        }
    }

    void BindTexture(GLuint unit, GLenum target, GLuint texture) {
        assert(unit < kMaxTextureUnits && "Texture unit out of range");
        if (unit >= kMaxTextureUnits) {
            // Fallback: skip cache, call driver directly.
            if (unit != activeTextureUnit_) {
                glActiveTexture(GL_TEXTURE0 + unit);
                activeTextureUnit_ = unit;
            }
            glBindTexture(target, texture);
            return;
        }
        if (unit != activeTextureUnit_) {
            glActiveTexture(GL_TEXTURE0 + unit);
            activeTextureUnit_ = unit;
        }
        auto& slot = boundTextures_[unit];
        if (texture != slot.id || target != slot.target) {
            glBindTexture(target, texture);
            slot.id = texture;
            slot.target = target;
        }
    }

    void UseProgram(GLuint program) {
        if (program != currentProgram_) {
            glUseProgram(program);
            currentProgram_ = program;
        }
    }

    void BindFramebuffer(GLenum target, GLuint fbo) {
        if (target == GL_FRAMEBUFFER || target == GL_DRAW_FRAMEBUFFER) {
            if (fbo != boundDrawFBO_) {
                glBindFramebuffer(target, fbo);
                boundDrawFBO_ = fbo;
                if (target == GL_FRAMEBUFFER) boundReadFBO_ = fbo;
            } else if (target == GL_FRAMEBUFFER && fbo != boundReadFBO_) {
                glBindFramebuffer(target, fbo);
                boundReadFBO_ = fbo;
            }
        } else { // GL_READ_FRAMEBUFFER
            if (fbo != boundReadFBO_) {
                glBindFramebuffer(target, fbo);
                boundReadFBO_ = fbo;
            }
        }
    }

    // ----- Deletion notifications (call AFTER glDelete*) -----
    //
    // IMPORTANT — Cross-thread shared resource deletion:
    // This cache is thread_local (one instance per EGL context/thread).
    // Notify*Deleted() only invalidates the CURRENT thread's cache.
    //
    // If multiple threads share GL objects (via EGL shared contexts), deleting
    // a shared buffer/texture from a worker thread will NOT automatically
    // invalidate the render thread's cache. Two safe patterns:
    //   1. (Preferred) Only delete shared resources from the thread that owns
    //      the cache entry — i.e., the render thread that bound them.
    //   2. After cross-thread deletion, the render thread must call
    //      GLStateCache::Instance().NotifyBufferDeleted(id) before next use,
    //      or call Invalidate() to clear all cached state.
    //
    // GL spec note: after glDeleteBuffers, the name becomes unused and all
    // bindings in the CURRENT context are reset to 0. Other shared contexts
    // retain stale bindings until they rebind — which mirrors our cache model.

    void NotifyBufferDeleted(GLuint id) {
        if (boundEBO_ == id) boundEBO_ = kUnknown;
        for (auto& b : boundBuffers_) { if (b == id) b = kUnknown; }
    }

    void NotifyTextureDeleted(GLuint id) {
        for (auto& t : boundTextures_) { if (t.id == id) { t.id = kUnknown; t.target = 0; } }
    }

    void NotifyVAODeleted(GLuint id) {
        if (boundVAO_ == id) { boundVAO_ = kUnknown; boundEBO_ = kUnknown; }
    }

    void NotifyFBODeleted(GLuint id) {
        if (boundDrawFBO_ == id) boundDrawFBO_ = kUnknown;
        if (boundReadFBO_ == id) boundReadFBO_ = kUnknown;
    }

    void NotifyProgramDeleted(GLuint id) {
        if (currentProgram_ == id) currentProgram_ = kUnknown;
    }

    // ----- Full invalidation (call after eglMakeCurrent / context loss) -----

    void Invalidate() {
        boundVAO_ = kUnknown;
        boundEBO_ = kUnknown;
        for (auto& b : boundBuffers_) b = kUnknown;
        for (auto& t : boundTextures_) { t.id = kUnknown; t.target = 0; }
        currentProgram_ = kUnknown;
        boundDrawFBO_ = kUnknown;
        boundReadFBO_ = kUnknown;
        activeTextureUnit_ = kUnknown;
    }

private:
    GLStateCache() { Invalidate(); }

    /// Returns pointer to the cache slot for a known target, or nullptr for
    /// unrecognised targets (caller must issue the driver call directly).
    GLuint* GetBufferSlot(GLenum target) {
        switch (target) {
            case GL_ARRAY_BUFFER:              return &boundBuffers_[0];
            case GL_UNIFORM_BUFFER:            return &boundBuffers_[1];
            case GL_SHADER_STORAGE_BUFFER:     return &boundBuffers_[2];
            case GL_COPY_READ_BUFFER:          return &boundBuffers_[3];
            case GL_COPY_WRITE_BUFFER:         return &boundBuffers_[4];
            case GL_PIXEL_PACK_BUFFER:         return &boundBuffers_[5];
            case GL_PIXEL_UNPACK_BUFFER:       return &boundBuffers_[6];
            case GL_TRANSFORM_FEEDBACK_BUFFER: return &boundBuffers_[7];
            case GL_DRAW_INDIRECT_BUFFER:      return &boundBuffers_[8];
            case GL_DISPATCH_INDIRECT_BUFFER:  return &boundBuffers_[9];
            case GL_ATOMIC_COUNTER_BUFFER:     return &boundBuffers_[10];
            default:                           return nullptr; // Not cached
        }
    }

    struct TextureSlot {
        GLuint id = kUnknown;
        GLenum target = 0;
    };

    GLuint boundVAO_ = kUnknown;
    GLuint boundEBO_ = kUnknown;
    GLuint boundBuffers_[11] = {}; // One slot per known non-EBO target
    TextureSlot boundTextures_[kMaxTextureUnits] = {};
    GLuint currentProgram_ = kUnknown;
    GLuint boundDrawFBO_ = kUnknown;
    GLuint boundReadFBO_ = kUnknown;
    GLuint activeTextureUnit_ = kUnknown;
};

// ============================================================================
// RAII Buffer Object (VBO / EBO / PBO)
// ============================================================================
class GLBuffer {
public:
    GLBuffer() = default;
    ~GLBuffer() { Destroy(); }

    // Non-copyable
    GLBuffer(const GLBuffer&) = delete;
    GLBuffer& operator=(const GLBuffer&) = delete;

    // Movable
    GLBuffer(GLBuffer&& other) noexcept
        : id_(other.id_), target_(other.target_), size_(other.size_) {
        other.id_ = 0;
    }
    GLBuffer& operator=(GLBuffer&& other) noexcept {
        if (this != &other) {
            Destroy();
            id_ = other.id_; target_ = other.target_; size_ = other.size_;
            other.id_ = 0;
        }
        return *this;
    }

    /// Create buffer with initial data (or nullptr for dynamic)
    bool Create(GLenum target, const void* data, GLsizeiptr size, GLenum usage) {
        Destroy();
        target_ = target;
        size_ = size;

        glGenBuffers(1, &id_);
        if (id_ == 0) return false;

        GLStateCache::Instance().BindBuffer(target_, id_);
        glBufferData(target_, size, data, usage);
        return true;
    }

    /// Update sub-region (partial update)
    void SubData(GLintptr offset, GLsizeiptr size, const void* data) {
        assert(id_ != 0);
        GLStateCache::Instance().BindBuffer(target_, id_);
        glBufferSubData(target_, offset, size, data);
    }

    /// Orphan + remap for full dynamic update (avoids GPU sync stall on TBDR)
    /// Usage: auto ptr = buffer.MapForWrite(fullSize); memcpy(ptr, data, size); buffer.Unmap();
    void* MapForWrite(GLsizeiptr size) {
        assert(id_ != 0);
        GLStateCache::Instance().BindBuffer(target_, id_);
        // GL_MAP_INVALIDATE_BUFFER_BIT orphans old storage — no sync wait
        void* ptr = glMapBufferRange(target_, 0, size,
                                     GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT);
        return ptr;
    }

    void Unmap() {
        GLStateCache::Instance().BindBuffer(target_, id_);
        glUnmapBuffer(target_);
    }

    void Bind() const {
        GLStateCache::Instance().BindBuffer(target_, id_);
    }

    GLuint Id() const { return id_; }
    GLsizeiptr Size() const { return size_; }
    bool IsValid() const { return id_ != 0; }

    void Destroy() {
        if (id_ != 0) {
            glDeleteBuffers(1, &id_);
            GLStateCache::Instance().NotifyBufferDeleted(id_);
            id_ = 0;
        }
    }

private:
    GLuint id_ = 0;
    GLenum target_ = GL_ARRAY_BUFFER;
    GLsizeiptr size_ = 0;
};

// ============================================================================
// RAII Vertex Array Object with attribute setup
// ============================================================================
class VertexArrayObject {
public:
    VertexArrayObject() = default;
    ~VertexArrayObject() { Destroy(); }

    // Non-copyable
    VertexArrayObject(const VertexArrayObject&) = delete;
    VertexArrayObject& operator=(const VertexArrayObject&) = delete;

    // Movable
    VertexArrayObject(VertexArrayObject&& other) noexcept : id_(other.id_) {
        other.id_ = 0;
    }
    VertexArrayObject& operator=(VertexArrayObject&& other) noexcept {
        if (this != &other) {
            Destroy();
            id_ = other.id_;
            other.id_ = 0;
        }
        return *this;
    }

    bool Create() {
        Destroy();
        glGenVertexArrays(1, &id_);
        return id_ != 0;
    }

    void Bind() const {
        assert(id_ != 0);
        GLStateCache::Instance().BindVertexArray(id_);
    }

    /// Define a vertex attribute (call while VAO is bound)
    void SetAttribute(GLuint location, GLint size, GLenum type,
                      GLboolean normalized, GLsizei stride, const void* offset) {
        Bind();
        glEnableVertexAttribArray(location);
        glVertexAttribPointer(location, size, type, normalized, stride, offset);
    }

    /// Define an integer vertex attribute (no normalization)
    void SetAttributeI(GLuint location, GLint size, GLenum type,
                       GLsizei stride, const void* offset) {
        Bind();
        glEnableVertexAttribArray(location);
        glVertexAttribIPointer(location, size, type, stride, offset);
    }

    /// Set attribute divisor for instanced rendering
    void SetAttributeDivisor(GLuint location, GLuint divisor) {
        Bind();
        glVertexAttribDivisor(location, divisor);
    }

    /// Attach an element buffer (EBO/IBO) to this VAO.
    /// Routes through the cache to keep boundEBO_ in sync.
    void SetElementBuffer(const GLBuffer& ebo) {
        Bind();
        GLStateCache::Instance().BindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo.Id());
    }

    GLuint Id() const { return id_; }
    bool IsValid() const { return id_ != 0; }

    void Destroy() {
        if (id_ != 0) {
            glDeleteVertexArrays(1, &id_);
            GLStateCache::Instance().NotifyVAODeleted(id_);
            id_ = 0;
        }
    }

private:
    GLuint id_ = 0;
};

// ============================================================================
// Convenience: Mesh class combining VAO + VBO + EBO
// ============================================================================
struct VertexAttribute {
    GLuint location;
    GLint  size;       // components (1-4)
    GLenum type;       // GL_FLOAT, GL_UNSIGNED_BYTE, etc.
    GLboolean normalized;
    GLsizei stride;
    size_t offset;
};

class Mesh {
public:
    Mesh() = default;
    ~Mesh() = default;
    Mesh(Mesh&&) = default;
    Mesh& operator=(Mesh&&) = default;

    /// Create mesh from interleaved vertex data + index data
    bool Create(const void* vertices, GLsizeiptr vertexSize,
                const void* indices, GLsizeiptr indexSize,
                const std::vector<VertexAttribute>& attributes,
                GLenum indexType = GL_UNSIGNED_SHORT) {
        indexType_ = indexType;
        indexCount_ = static_cast<GLsizei>(
            indexSize / (indexType == GL_UNSIGNED_SHORT ? sizeof(GLushort) : sizeof(GLuint)));

        // Create VBO
        if (!vbo_.Create(GL_ARRAY_BUFFER, vertices, vertexSize, GL_STATIC_DRAW))
            return false;

        // Create EBO
        if (!ebo_.Create(GL_ELEMENT_ARRAY_BUFFER, indices, indexSize, GL_STATIC_DRAW))
            return false;

        // Create and configure VAO
        if (!vao_.Create()) return false;
        vao_.Bind();
        vbo_.Bind();

        for (const auto& attr : attributes) {
            vao_.SetAttribute(attr.location, attr.size, attr.type,
                              attr.normalized, attr.stride,
                              reinterpret_cast<const void*>(attr.offset));
        }

        vao_.SetElementBuffer(ebo_);

        // Unbind VAO to avoid accidental state pollution
        GLStateCache::Instance().BindVertexArray(0);
        return true;
    }

    /// Draw the mesh (assumes correct program is bound)
    void Draw() const {
        vao_.Bind();
        glDrawElements(GL_TRIANGLES, indexCount_, indexType_, nullptr);
    }

    /// Draw instanced
    void DrawInstanced(GLsizei instanceCount) const {
        vao_.Bind();
        glDrawElementsInstanced(GL_TRIANGLES, indexCount_, indexType_,
                                nullptr, instanceCount);
    }

    bool IsValid() const { return vao_.IsValid() && vbo_.IsValid() && ebo_.IsValid(); }

private:
    VertexArrayObject vao_;
    GLBuffer vbo_;
    GLBuffer ebo_;
    GLsizei indexCount_ = 0;
    GLenum indexType_ = GL_UNSIGNED_SHORT;
};

// ============================================================================
// Usage Example
// ============================================================================
/*
    // Define a simple triangle mesh
    struct Vertex {
        float position[3];
        float normal[3];
        float texcoord[2];
    };

    std::vector<Vertex> vertices = { ... };
    std::vector<uint16_t> indices = { 0, 1, 2, ... };

    Mesh mesh;
    std::vector<VertexAttribute> attrs = {
        { 0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), offsetof(Vertex, position) },
        { 1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), offsetof(Vertex, normal) },
        { 2, 2, GL_FLOAT, GL_FALSE, sizeof(Vertex), offsetof(Vertex, texcoord) },
    };

    mesh.Create(vertices.data(), vertices.size() * sizeof(Vertex),
                indices.data(), indices.size() * sizeof(uint16_t),
                attrs);

    // In render loop:
    GLStateCache::Instance().UseProgram(shaderProgram);
    mesh.Draw();

    // Dynamic buffer update (e.g., particle positions):
    GLBuffer dynamicVbo;
    dynamicVbo.Create(GL_ARRAY_BUFFER, nullptr, maxParticles * sizeof(Particle), GL_DYNAMIC_DRAW);
    // Each frame:
    void* ptr = dynamicVbo.MapForWrite(activeCount * sizeof(Particle));
    memcpy(ptr, cpuParticles, activeCount * sizeof(Particle));
    dynamicVbo.Unmap();
*/
