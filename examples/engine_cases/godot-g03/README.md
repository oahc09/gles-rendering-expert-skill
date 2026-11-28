# Godot Compatibility · G03 战斗回放

固定 Godot 4.5.1 stable（`f62fdbde15035c5576dad93e586201f4d41ef0cb`），场景和网格均由仓库内 GDScript 生成，使用项目软件许可证。Linux 官方 x86_64 ZIP 的 SHA-512 为 `5bccbed65a94b82c7c319fdb15719ee8113a6e503976cc54e16f1c61fe95f3d74e5e40b8449b5bb89ff7f424574c20af01a4f5ef08b389e4dc338b245185b0b9`。 [官方版本](https://github.com/godotengine/godot/releases/tag/4.5.1-stable)

在可用的 X11 会话里运行。将回执写到源码树外的已存在目录。

```sh
godot --path examples/engine_cases/godot-g03 --display-driver x11 \
  --rendering-method gl_compatibility --rendering-driver opengl3_es --audio-driver Dummy \
  -- --require-driver=opengl3_es --receipt=/tmp/g03.json
```

固定 seed 1337，按 0 → 12 → 48 → 12 实例运行四个取样点。零实例图像须无黄色角色且不可拾取哨兵。其余阶段画面须包含角色、HUD、粒子并通过哨兵射线拾取。扩容后保留 48 容量，收缩通过 visible count 完成。输出四张实际视口读回、源文件哈希、引擎版本、驱动、GPU 名称、draw call 与 CPU 脚本更新时间。GPU 时间和上传时间在当前收集器中为 `null`。

初次运行中，0 → 12 后有碰撞但角色在视口中缺失。此场景现在为 MultiMesh 指定覆盖动画范围的 AABB，并在写完变换后发布可见数量。

当前覆盖 G03、B03、B09 和 B17 的基础子集。后续仍需 Android 原生运行、蒙皮、LOD、负缩放、完整裁剪和远距离回放，物理 GPU 和 Android 性能单独验收。 [Godot Compatibility 渲染器](https://docs.godotengine.org/en/4.5/tutorials/rendering/renderers.html)
