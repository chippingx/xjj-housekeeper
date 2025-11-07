# 应用图标

- 推荐提供 `xjj.icns`（macOS）位于本目录：`assets/icons/xjj.icns`。
- 若暂未提供图标，打包脚本将使用默认系统图标。
- 可从 `xjj.png` 生成 `.icns`：
  - 使用 macOS 自带工具：
    ```bash
    # 将 1024x1024 的 PNG 生成 ICNS（需先创建 .iconset）
    mkdir xjj.iconset
    sips -z 16 16     xjj.png --out xjj.iconset/icon_16x16.png
    sips -z 32 32     xjj.png --out xjj.iconset/icon_16x16@2x.png
    sips -z 32 32     xjj.png --out xjj.iconset/icon_32x32.png
    sips -z 64 64     xjj.png --out xjj.iconset/icon_32x32@2x.png
    sips -z 128 128   xjj.png --out xjj.iconset/icon_128x128.png
    sips -z 256 256   xjj.png --out xjj.iconset/icon_128x128@2x.png
    sips -z 256 256   xjj.png --out xjj.iconset/icon_256x256.png
    sips -z 512 512   xjj.png --out xjj.iconset/icon_256x256@2x.png
    sips -z 512 512   xjj.png --out xjj.iconset/icon_512x512.png
    cp xjj.png xjj.iconset/icon_512x512@2x.png
    iconutil -c icns xjj.iconset -o xjj.icns
    mv xjj.icns assets/icons/xjj.icns
    ```
- 打包脚本会自动检测 `assets/icons/xjj.icns` 并应用到 `.app`。