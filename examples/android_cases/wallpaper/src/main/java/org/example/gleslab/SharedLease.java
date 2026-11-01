package org.example.gleslab;

import java.util.function.Consumer;
import java.util.function.Supplier;

/** One shared resource lifecycle, explicit independent owner handles; all changes serialized. */
final class SharedLease<T> {
    private final Supplier<T> open;
    private final Consumer<T> dispose;
    private T resource;
    private int owners;
    SharedLease(Supplier<T> open, Consumer<T> dispose) { this.open = open; this.dispose = dispose; }
    synchronized Handle acquire() {
        if (owners == 0) {
            T created = open.get(); // Failure must not publish or increment owners.
            if (created == null) throw new IllegalStateException("null shared resource");
            resource = created;
        }
        owners++;
        return new Handle(resource);
    }
    final class Handle implements AutoCloseable {
        final T value;
        private boolean closed;
        private Handle(T value) { this.value = value; }
        @Override public void close() {
            synchronized (SharedLease.this) {
                if (closed) return;
                closed = true;
                if (--owners == 0) {
                    T last = resource; resource = null;
                    dispose.accept(last);
                }
            }
        }
    }
}
