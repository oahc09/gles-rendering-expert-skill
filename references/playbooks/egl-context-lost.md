# EGL recovery and resource-leak diagnostic

**C04:** `APP_CMD_CONTEXT_LOST` is not an Android native-app-glue command. Handle actual window lifecycle callbacks and EGL failure returns. Read the error directly after the failed call; a later EGL call can obscure evidence.

State transitions:

```text
NO_WINDOW -> HAVE_WINDOW -> SURFACE_CURRENT -> RENDERING
RENDERING -- window destroyed/BAD_SURFACE --> NO_SURFACE (context may survive)
any current state -- CONTEXT_LOST --> REBUILD_SHARE_GROUP
REBUILD_SHARE_GROUP -> new context + asset upload + local state -> SURFACE_CURRENT
```

* `EGL_BAD_SURFACE`: stop submission; unbind safely, discard stale surface/native-window reference, recreate a compatible surface when a valid window exists. Do not infer that shared textures disappeared.
* `EGL_CONTEXT_LOST`: reject stale generation handles; destroy/recreate context/share-group dependent state, rebuild GL resources from CPU assets, re-query capabilities. Sync objects and cached program/object handles are not portable across recreated contexts.
* Shared-context ownership is explicit; serialize lifecycle work with worker submissions. Stop/join upload workers before destroying their display/context. Texture storage may be shared, but VAO/FBO bindings are context-local; cleanup on the appropriate owner.
* A retry is bounded and logged. Repeated failure returns a visible error/fallback rather than an infinite create loop.

Repro: repeated window teardown, orientation resize, background/foreground, then controlled renderer restart with resource counts. A controlled restart tests application rebuilding, **not** real driver context loss. Forced pbuffer recreation tests surface handling, **not** Android window events. Compare allocations after cycles; distinguish GPU allocator caches from growing live object counts.

Sources: [EGL specification](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf), [native activity API](https://developer.android.com/ndk/reference/group/native-activity). See [lifecycle matrix](../matrices/backend-device-matrix.md).
