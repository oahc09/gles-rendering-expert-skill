// SPDX-License-Identifier: MIT
#pragma once
#include <stdexcept>
#include <thread>
namespace pressure {
enum class Completion { Pending, Complete, Failed };
// Pure policy: injected statuses are NOT measurements of a real GPU fence.
struct CompletionPolicy {
    bool canceled=false, completed=false, failed=false;
    void cancel() { canceled=true; }
    void observe(Completion result) {
        if(result==Completion::Failed) failed=true;
        if(result==Completion::Complete && !failed) completed=true;
    }
    bool can_consume() const { return completed && !canceled && !failed; }
    bool can_recycle() const { return completed && !failed; }
};
struct Owner {
    std::thread::id thread=std::this_thread::get_id();
    unsigned generation=0;
    void check(unsigned currentGeneration) const {
        if(thread!=std::this_thread::get_id() || generation!=currentGeneration)
            throw std::logic_error("resource owner thread/context generation mismatch");
    }
};
}
