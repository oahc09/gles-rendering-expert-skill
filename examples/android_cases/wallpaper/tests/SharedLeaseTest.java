package org.example.gleslab;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Host concurrency checks only; lifecycle callbacks stand in for EGL. */
public final class SharedLeaseTest {
    private static int checks;
    private static void check(boolean value) { checks++; if (!value) throw new AssertionError("lease check " + checks); }
    public static void main(String[] args) throws Exception {
        AtomicInteger opened = new AtomicInteger(), closed = new AtomicInteger();
        SharedLease<Object> pool = new SharedLease<>(() -> { opened.incrementAndGet(); return new Object(); }, value -> closed.incrementAndGet());
        SharedLease<Object>.Handle a = pool.acquire(), b = pool.acquire();
        check(a.value == b.value); check(opened.get() == 1);
        a.close(); check(closed.get() == 0);
        a.close(); check(closed.get() == 0);
        b.close(); check(closed.get() == 1);
        SharedLease<Object>.Handle next = pool.acquire();
        check(next.value != a.value); check(opened.get() == 2);
        next.close(); check(closed.get() == 2);
        AtomicInteger attempts = new AtomicInteger();
        SharedLease<Object> failures = new SharedLease<>(() -> {
            if (attempts.incrementAndGet() == 1) throw new IllegalStateException("injected init failure");
            return new Object();
        }, value -> {});
        try { failures.acquire(); throw new AssertionError("failed init accepted"); } catch (IllegalStateException expected) { check(true); }
        failures.acquire().close(); check(attempts.get() == 2);
        CountDownLatch acquired = new CountDownLatch(8), release = new CountDownLatch(1);
        AtomicReference<Throwable> error = new AtomicReference<>();
        Thread[] workers = new Thread[8];
        for (int i=0;i<workers.length;i++) {
            workers[i]=new Thread(() -> {
                SharedLease<Object>.Handle h=null;
                try { h=pool.acquire(); acquired.countDown(); release.await(); }
                catch(Throwable e) { error.compareAndSet(null,e); }
                finally { if(h!=null)h.close(); }
            }); workers[i].start();
        }
        acquired.await(); check(opened.get()==3);check(closed.get()==2); release.countDown();
        for(Thread worker:workers)worker.join();
        check(error.get()==null);check(closed.get()==3);
        System.out.println("SHARED_LEASE_CHECKS="+checks+" PASS; EGL driver=NOT_RUN");
    }
}
