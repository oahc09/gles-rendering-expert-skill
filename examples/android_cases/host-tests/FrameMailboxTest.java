package org.example.gleslab;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public final class FrameMailboxTest {
    private static void check(boolean condition, String caseName) {
        if (!condition) throw new AssertionError(caseName);
    }

    public static void main(String[] args) throws Exception {
        FrameMailbox<Object> mailbox = new FrameMailbox<>();
        Object oldConsumer = new Object();
        Object newConsumer = new Object();
        FrameMailbox.Registration<Object> oldRegistration = mailbox.register(oldConsumer);
        check(mailbox.offer(oldRegistration, oldConsumer), "old real frame");
        check(!mailbox.offer(oldRegistration, oldConsumer), "same generation coalesces");

        // Producer callback was dispatched, but deliberately does not reach the
        // mailbox until the GL owner has retired and installed a new consumer.
        CountDownLatch dispatched = new CountDownLatch(1);
        CountDownLatch replacementReady = new CountDownLatch(1);
        AtomicBoolean staleRequestedRender = new AtomicBoolean(true);
        Thread late = new Thread(() -> {
            dispatched.countDown();
            try {
                if (replacementReady.await(5, TimeUnit.SECONDS)) {
                    staleRequestedRender.set(mailbox.offer(oldRegistration, oldConsumer));
                }
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
            }
        });
        late.start();
        check(dispatched.await(5, TimeUnit.SECONDS), "callback dispatched");
        mailbox.retire();
        check(!mailbox.offer(oldRegistration, oldConsumer), "retired callback rejected before replacement");
        FrameMailbox.Registration<Object> fresh = mailbox.register(newConsumer);
        replacementReady.countDown();
        late.join(5000);
        check(!late.isAlive() && !staleRequestedRender.get(), "stale callback rejected after replacement");
        check(!mailbox.take(newConsumer), "fresh texture not acquired with old signal");
        check(!mailbox.offer(fresh, oldConsumer), "mismatched callback object");
        check(mailbox.offer(fresh, newConsumer), "fresh frame requests render");
        check(!mailbox.take(oldConsumer), "old owner cannot drain fresh signal");
        check(mailbox.take(newConsumer) && !mailbox.take(newConsumer), "fresh signal drains exactly once");

        // Object identity alone is insufficient if it is registered again.
        FrameMailbox.Registration<Object> reregistered = mailbox.register(newConsumer);
        check(!mailbox.offer(fresh, newConsumer), "previous listener rejected on same object");
        check(mailbox.offer(reregistered, newConsumer), "new listener on same object accepted");
        mailbox.retire();
        check(!mailbox.take(newConsumer), "teardown drops unconsumed signal");
        System.out.println("PASS: SurfaceTexture registration mailbox");
    }
}
