package org.example.gleslab.filament;

import android.app.Activity;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Choreographer;
import android.view.PixelCopy;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.google.android.filament.Camera;
import com.google.android.filament.Engine;
import com.google.android.filament.EntityManager;
import com.google.android.filament.IndirectLight;
import com.google.android.filament.LightManager;
import com.google.android.filament.Renderer;
import com.google.android.filament.Scene;
import com.google.android.filament.SwapChain;
import com.google.android.filament.View;
import com.google.android.filament.Viewport;
import com.google.android.filament.gltfio.AssetLoader;
import com.google.android.filament.gltfio.FilamentAsset;
import com.google.android.filament.gltfio.Gltfio;
import com.google.android.filament.gltfio.ResourceLoader;
import com.google.android.filament.gltfio.UbershaderProvider;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Fixed G06 viewer. The Activity thread owns native object creation and retirement. */
public final class ViewerActivity extends Activity implements SurfaceHolder.Callback, Choreographer.FrameCallback {
    private static final String TAG = "GLESFilamentG06";
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private SurfaceView surface;
    private TextView status;
    private Engine engine;
    private Renderer renderer;
    private Scene scene;
    private View renderView;
    private Camera camera;
    private IndirectLight light;
    private AssetLoader assets;
    private ResourceLoader resources;
    private UbershaderProvider materials;
    private SwapChain swapChain;
    private FilamentAsset model;
    private int cameraEntity;
    private int sunEntity;
    private int surfaceGeneration;
    private int modelGeneration;
    private int surfaceWidth;
    private int surfaceHeight;
    private String currentAsset = "amber";
    private boolean highLight = true;
    private boolean running;
    private boolean rendered;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        Gltfio.init();
        engine = Engine.create(Engine.Backend.OPENGL);
        if (engine.getBackend() != Engine.Backend.OPENGL) throw new IllegalStateException("OpenGL required");
        renderer = engine.createRenderer();
        Renderer.ClearOptions clear = new Renderer.ClearOptions();
        clear.clear = true;
        clear.clearColor = new float[]{0.03f, 0.055f, 0.09f, 1.0f};
        renderer.setClearOptions(clear);
        scene = engine.createScene();
        renderView = engine.createView();
        renderView.setScene(scene);
        cameraEntity = EntityManager.get().create();
        camera = engine.createCamera(cameraEntity);
        camera.lookAt(2.2, 1.6, 3.5, 0, 0, 0, 0, 1, 0);
        renderView.setCamera(camera);
        light = new IndirectLight.Builder().irradiance(1, new float[]{0.8f, 0.8f, 0.8f})
                .intensity(20_000).build(engine);
        scene.setIndirectLight(light);
        sunEntity = EntityManager.get().create();
        new LightManager.Builder(LightManager.Type.DIRECTIONAL)
                .direction(-0.55f, -0.9f, -0.5f).intensity(65_000).build(engine, sunEntity);
        scene.addEntity(sunEntity);
        materials = new UbershaderProvider(engine);
        assets = new AssetLoader(engine, materials, EntityManager.get());
        resources = new ResourceLoader(engine);

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setFitsSystemWindows(true);
        status = new TextView(this);
        status.setPadding(16, 8, 16, 8);
        container.addView(status);
        surface = new SurfaceView(this);
        surface.getHolder().addCallback(this);
        surface.setContentDescription("Product model, tap to pick");
        surface.setOnTouchListener((view, event) -> {
            if (event.getAction() == android.view.MotionEvent.ACTION_UP) {
                view.performClick();
                pick((int) event.getX(), (int) event.getY());
            }
            return true;
        });
        container.addView(surface, new LinearLayout.LayoutParams(-1, 0, 1.0f));
        LinearLayout actions = new LinearLayout(this);
        actions.addView(button("Switch model", () -> load(currentAsset.equals("amber") ? "blue" : "amber", false)));
        actions.addView(button("Lighting", () -> {
            highLight = !highLight;
            light.setIntensity(highLight ? 20_000 : 3_000);
            report("IBL level " + (highLight ? "high" : "low"));
        }));
        container.addView(actions);
        LinearLayout evidence = new LinearLayout(this);
        evidence.addView(button("Thumbnail", this::captureThumbnail));
        evidence.addView(button("Test fallback", () -> load(currentAsset, true)));
        container.addView(evidence);
        load(currentAsset, false);
        setContentView(container);
    }

    private Button button(String label, Runnable action) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(view -> action.run());
        return button;
    }

    private void load(String name, boolean control) {
        FilamentAsset replacement = null;
        try (InputStream stream = getAssets().open(name + ".gltf")) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] chunk = new byte[4096];
            for (int size; (size = stream.read(chunk)) != -1; ) bytes.write(chunk, 0, size);
            byte[] raw = bytes.toByteArray();
            JSONObject gltf = new JSONObject(new String(raw, StandardCharsets.UTF_8));
            if (control) gltf.put("extensionsRequired", new JSONArray().put("GLES_LAB_unsupported"));
            JSONArray required = gltf.optJSONArray("extensionsRequired");
            if (required != null && required.length() > 0) {
                report("Rejected required extension, retained " + currentAsset);
                return;
            }
            ByteBuffer payload = ByteBuffer.allocateDirect(raw.length);
            payload.put(raw).flip();
            replacement = assets.createAsset(payload);
            if (replacement == null || replacement.getRenderableEntities().length == 0) {
                throw new IllegalArgumentException("No renderable entities");
            }
            resources.loadResources(replacement);
            replacement.releaseSourceData();
            releaseModel();
            model = replacement;
            replacement = null;
            scene.addEntities(model.getEntities());
            currentAsset = name;
            modelGeneration++;
            rendered = false;
            report("Loaded " + name + " | backend=" + engine.getBackend());
        } catch (Exception error) {
            if (replacement != null) assets.destroyAsset(replacement);
            Log.e(TAG, "Model load failed", error);
            report("Model load failed | retained " + (model == null ? "none" : currentAsset));
        }
    }

    private void releaseModel() {
        if (model == null) return;
        scene.removeEntities(model.getEntities());
        assets.destroyAsset(model);
        model = null;
    }

    private void pick(int x, int y) {
        if (!rendered || model == null) return;
        int generation = modelGeneration;
        int drawable = surfaceGeneration;
        renderView.pick(x, surface.getHeight() - 1 - y, mainHandler, result -> {
            if (engine == null || generation != modelGeneration || drawable != surfaceGeneration || model == null) return;
            boolean hit = Arrays.stream(model.getRenderableEntities()).anyMatch(entity -> entity == result.renderable);
            report("Pick " + (hit ? "hit " + currentAsset : "miss"));
        });
    }

    private void captureThumbnail() {
        if (!rendered || swapChain == null || surfaceWidth <= 0 || surfaceHeight <= 0) return;
        int generation = modelGeneration;
        int drawable = surfaceGeneration;
        String name = currentAsset;
        int height = Math.max(1, Math.min(384, 192 * surfaceHeight / surfaceWidth));
        Bitmap source = Bitmap.createBitmap(192, height, Bitmap.Config.ARGB_8888);
        PixelCopy.request(surface, source, result -> {
            try {
                if (engine == null || generation != modelGeneration || drawable != surfaceGeneration) return;
                if (result != PixelCopy.SUCCESS) {
                    report("Thumbnail readback failed " + result);
                    return;
                }
                try (FileOutputStream out = new FileOutputStream(new File(getFilesDir(), name + "-thumbnail.png"))) {
                    report(source.compress(Bitmap.CompressFormat.PNG, 100, out)
                            ? "Saved thumbnail " + name : "Thumbnail write failed");
                }
            } catch (Exception error) {
                Log.e(TAG, "Thumbnail write failed", error);
            } finally {
                source.recycle();
            }
        }, mainHandler);
    }

    private void report(String text) {
        status.setText(text);
        Log.i(TAG, text + " | modelGeneration=" + modelGeneration + " surfaceGeneration=" + surfaceGeneration);
    }

    @Override protected void onResume() {
        super.onResume();
        running = true;
        Choreographer.getInstance().postFrameCallback(this);
    }

    @Override protected void onPause() {
        running = false;
        Choreographer.getInstance().removeFrameCallback(this);
        super.onPause();
    }

    @Override public void doFrame(long frameTimeNanos) {
        if (!running) return;
        if (swapChain != null && renderer.beginFrame(swapChain, frameTimeNanos)) {
            renderer.render(renderView);
            renderer.endFrame();
            rendered = true;
        }
        Choreographer.getInstance().postFrameCallback(this);
    }

    @Override public void surfaceCreated(SurfaceHolder holder) {
        swapChain = engine.createSwapChain(holder.getSurface());
        surfaceGeneration++;
    }

    @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        if (width <= 0 || height <= 0) return;
        if (surfaceWidth != width || surfaceHeight != height) {
            surfaceGeneration++;
            rendered = false;
        }
        surfaceWidth = width;
        surfaceHeight = height;
        renderView.setViewport(new Viewport(0, 0, width, height));
        camera.setProjection(42, (double) width / height, 0.1, 30, Camera.Fov.VERTICAL);
    }

    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        releaseSurface();
    }

    private void releaseSurface() {
        if (swapChain == null) return;
        surfaceGeneration++;
        rendered = false;
        surfaceWidth = surfaceHeight = 0;
        engine.destroySwapChain(swapChain);
        engine.flushAndWait();
        swapChain = null;
    }

    @Override protected void onDestroy() {
        surface.getHolder().removeCallback(this);
        releaseSurface();
        releaseModel();
        resources.destroy();
        assets.destroy();
        materials.destroyMaterials();
        materials.destroy();
        scene.removeEntity(sunEntity);
        engine.destroyEntity(sunEntity);
        scene.setIndirectLight(null);
        engine.destroyIndirectLight(light);
        renderView.setCamera(null);
        renderView.setScene(null);
        engine.destroyView(renderView);
        engine.destroyRenderer(renderer);
        engine.destroyScene(scene);
        engine.destroyCameraComponent(cameraEntity);
        EntityManager.get().destroy(cameraEntity);
        EntityManager.get().destroy(sunEntity);
        engine.destroy();
        engine = null;
        super.onDestroy();
    }
}
