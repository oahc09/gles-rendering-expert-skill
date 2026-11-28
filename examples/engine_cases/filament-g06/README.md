# Filament Android · G06 商品查看

使用 Filament 和 gltfio 1.66.0，构建依赖见 `gradle.lockfile`。两份 glTF 2.0 资产均为本项目的程序化盒体，带自包含顶点和法线数据，以及不同的形状、基础色、metallic 和 roughness。 [Filament 版本源码](https://github.com/google/filament/tree/v1.66.0)

```sh
gradle -p examples/engine_cases/filament-g06 assembleDebug
```

应用在 Activity 线程上创建 OpenGL Engine。Surface 重建时替换 SwapChain，尺寸变化时更新 Viewport 与相机投影。装载新资产成功后才退休旧资产，无法支持的 required extension 保留旧资产。拾取和缩略图读回在回调中核对模型和 drawable generation。

固定操作为打开应用、切换两份模型、改变环境光强度、点击模型和空白处、保存缩略图、触发 required-extension 拒绝、退出重进。缩略图保存在应用私有目录的 `files/<资产>-thumbnail.png`。这是 G06 初始子集。后续仍需纹理色彩、蒙皮、透明材质、反射 IBL 与设备长时验收。

保存初始 amber、切换后的 blue、required-extension 拒绝后的 blue 和低环境光下的 blue 截图为 `amber.png`、`blue.png`、`blue-after-fallback.png`、`blue-low-light.png`。使用带 Pillow 13 的 Python 执行 `python examples/engine_cases/filament-g06/check_readbacks.py <截图目录>`，比较模型区域颜色、版本切换和回退误差。
