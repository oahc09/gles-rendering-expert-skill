package org.example.gleslab;

/** Coalesced frame notifications scoped to exactly one consumer registration. */
final class FrameMailbox<T> {
    static final class Registration<T> {
        private final T consumer;

        private Registration(T consumer) {
            this.consumer = consumer;
        }
    }

    private Registration<T> active;
    private boolean pending;

    synchronized Registration<T> register(T consumer) {
        if (consumer == null) throw new NullPointerException("consumer");
        active = new Registration<>(consumer);
        pending = false;
        return active;
    }

    /** A queued callback must still belong to the exact active registration. */
    synchronized boolean offer(Registration<T> registration, T source) {
        if (registration == null || registration != active || source != registration.consumer || pending) {
            return false;
        }
        pending = true;
        return true;
    }

    /** Called by the GL owner. A different consumer cannot steal the notification. */
    synchronized boolean take(T consumer) {
        if (active == null || consumer != active.consumer || !pending) return false;
        pending = false;
        return true;
    }

    synchronized void retire() {
        active = null;
        pending = false;
    }
}
