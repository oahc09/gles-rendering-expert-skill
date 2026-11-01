// SPDX-License-Identifier: MIT
package org.example.systemlab;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.ArrayList;

/** Two/four real SurfaceViews. --ez workers true selects per-surface schedulers.
 * Native EGL sections serialize and unbind on exit; no parallel-GPU speed claim.
 * This correctness demonstrator uses handler cadence, not a frame-pacing benchmark.
 */
public final class MultiSurfaceActivity extends Activity {
    static { System.loadLibrary("gles_system"); }
    private static native long create();
    private static native long attach(long lab, Surface surface);
    private static native void detach(long lab, long surface);
    private static native boolean draw(long lab, long surface);
    private static native void rebuild(long lab);
    private static native void destroy(long lab);
    private volatile long lab;
    private volatile boolean paused = true;
    private final ArrayList<Slot> slots = new ArrayList<>();
    private final ArrayList<HandlerThread> threads = new ArrayList<>();
    private TextView status;

    private final class Slot implements SurfaceHolder.Callback, Runnable {
        private volatile long key;
        private final Handler handler;
        Slot(Handler value) { handler = value; }
        @Override public void surfaceCreated(SurfaceHolder holder) {
            key = attach(lab, holder.getSurface());
            restart();
        }
        @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
            // Native queries current EGL surface dimensions each frame.
            restart();
        }
        @Override public void surfaceDestroyed(SurfaceHolder holder) {
            long old = key; key = 0;
            handler.removeCallbacks(this);
            // Synchronous native mutex joins any in-flight GL access before return.
            // A queued callback can only use a stale, never-reused registry handle.
            detach(lab, old);
        }
        void restart() { handler.removeCallbacks(this); if (!paused && key != 0) handler.post(this); }
        @Override public void run() {
            long current = key;
            if (paused || current == 0 || lab == 0) return;
            try { draw(lab, current); }
            catch (IllegalStateException error) {
                paused = true;
                runOnUiThread(() -> status.setText("Render stopped: " + error.getMessage()));
                return;
            }
            if (!paused && current == key) handler.postDelayed(this, 16);
        }
    }
    private Handler scheduler(String name) {
        HandlerThread thread = new HandlerThread(name); thread.start(); threads.add(thread);
        return new Handler(thread.getLooper());
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        status = new TextView(this); status.setText("Shared EGL group — device validation required"); root.addView(status);
        setContentView(root);
        try { lab = create(); } catch (IllegalStateException error) { status.setText("Unsupported: " + error.getMessage()); return; }
        boolean workers = getIntent().getBooleanExtra("workers", false);
        int count = getIntent().getIntExtra("surfaces", 2) == 4 ? 4 : 2;
        Handler common = workers ? null : scheduler("EGL-single");
        for (int i = 0; i < count; i++) {
            Slot slot = new Slot(workers ? scheduler("EGL-surface-" + i) : common); slots.add(slot);
            SurfaceView view = new SurfaceView(this); view.getHolder().addCallback(slot);
            root.addView(view, new LinearLayout.LayoutParams(-1, 0, 1));
        }
        Button reset = new Button(this); reset.setText("Controlled share-group rebuild (not real context loss)");
        reset.setOnClickListener(v -> { try { rebuild(lab); } catch (IllegalStateException error) { paused = true; status.setText(error.getMessage()); } }); root.addView(reset);
    }
    @Override protected void onResume() { super.onResume(); paused = false; for (Slot slot : slots) slot.restart(); }
    @Override protected void onPause() { paused = true; for (Slot slot : slots) slot.handler.removeCallbacks(slot); super.onPause(); }
    @Override protected void onDestroy() {
        paused = true;
        for (Slot slot : slots) { long old = slot.key; slot.key = 0; slot.handler.removeCallbacks(slot); detach(lab, old); }
        long oldLab = lab; lab = 0; destroy(oldLab);
        for (HandlerThread thread : threads) thread.quitSafely();
        super.onDestroy();
    }
}
