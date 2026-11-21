# Two-context EGLImage producer / consumer synchronization

```sh
python3 benchmarks/coverage/image-sync/run.py --config DRIVER.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/image-sync -p 'test_*.py' -v
```

Two real shared GLES contexts, one thread and one pbuffer switched sequentially. Producer renders a varying-alpha asymmetric RGBA8 4×4 image through a shader into a texture FBO. Image creation preserves content. Fence is inserted **after producer commands**, then producer glFlush executes before context switch. Consumer queues eglWaitSyncKHR, binds the image to an external texture and samples into pbuffer. CPU full readback checks independent analytic bytes. No glFinish occurs. Server wait is not a CPU completion guarantee; actual readback observes completion. Software scheduling may already finish the producer; this proves API synchronization flow + visible correct results, not a forced overlap/race or hardware queue-latency experiment.

Repeat for two distinct frames using a **new texture/image/fence per frame**, not unsafe mutation of shared storage. A second two-frame route uses eglClientWaitSyncKHR in at most100 calls of1ms each, requiring CONDITION_SATISFIED before sampling. TIMEOUT/failed wait aborts instead of reading without synchronization. Underlying driver/API latency is not wall-clock bounded. No FOREVER wait. Both extensions and exact KHR entrypoints are required; no core alias guessing. If capabilities are absent, exit77 UNSUPPORTED; client route here is an executed alternative, not an unsupported-server automatic dispatcher.

Both Mesa/ANGLE captured HOST_PASS: each8draws,4full64byte readbacks, zero byte error, two server and two client frames. Sync/image objects deleted after consumer readback, consumer external texture deleted, then producer FBO/source cleanup, consumer context destroyed, host teardown. Missing-fence and failed-wait checks are policy simulations only: no unsynchronized image read or fabricated stale-pixel negative is executed.

Source source hashes are consistency checks not authentication. No system metadata/raw handles archived. Physical GPU, Android AHB/protected/native buffer imports, concurrent threads, reusable-buffer mutation/orphan, timeline semaphores and performance gains are NOT_RUN/outside scope. Shared-context propagation cannot be generalized to arbitrary platforms. Pinned reviewed primary sources are in sources.json; no full specification text is distributed.

Each frame registers every owned object immediately after creation; cleanup clears successfully released entries and continues after a failed release, avoiding double destroy on retry. Partial-allocation and failed-release retry tests use mocks only, not claimed real GPU faults. Context/surface teardown return values are checked.
