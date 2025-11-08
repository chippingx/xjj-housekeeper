# XJJ 视频管理系统 - 启动指南

## 🚀 快速启动

### 🍎 macOS双击启动（推荐，免安装）

#### 浏览器版本 ⭐ 最稳定（基于 Streamlit）
```bash
# 双击这个文件
startup/XJJ-Browser.command
```

#### 桌面版本（原生 Tkinter 客户端）
```bash
# 双击这个文件
startup/XJJ-Desktop.command
```

### 🪟 Windows双击启动

#### 桌面版本（原生 Tkinter 客户端）
```bat
# 双击这个文件（Windows）
startup\\XJJ-Desktop.bat
```

### 使用方式

- 浏览器版（推荐）：双击 `startup/XJJ-Browser.command`，或运行 `poetry run python -m streamlit run ui/app.py --server.port 8501`。
- 桌面包装版：双击 `startup/XJJ-Desktop.command`，内部通过 `poetry run` 启动本地服务并嵌入到窗口。
- 若遇到依赖问题：在项目根目录执行 `poetry install` 后再运行脚本。

## 📁 文件说明

### 启动脚本
- `XJJ-Browser.command` — 浏览器版本（推荐，最稳定）
- `XJJ-Desktop.command` — 原生桌面客户端（Tkinter，独立于 Streamlit）
- `XJJ-Desktop.bat` — Windows 启动脚本（原生 Tkinter 客户端）
- `Build-XJJ-Desktop-App.command` — 打包 Tkinter 客户端为 macOS `.app`（可选图标）
- `Open-XJJ-Desktop-App.command` — 打开已打包的 `.app`


## 🛠️ 技术特性

### 自动化特性
- ✅ **自动安装依赖** - 首次运行使用 Poetry 自动安装项目依赖
- ✅ **环境检查** - 自动检查Python环境
- ✅ **用户级安装** - 不需要管理员权限
- ✅ **错误处理** - 友好的错误提示和解决建议

### 启动方式

#### 浏览器版本
- 通过 `ui/app.py` 入口启动（该入口保持兼容，实际代码位于 `ui/streamlit/`）
- 直接在默认浏览器中打开应用
- 最稳定可靠，兼容性最好，适合日常使用和开发调试

（已废弃）桌面窗口版本（Streamlit 包装）
已移除，改用原生 Tkinter 客户端。

#### 原生桌面客户端（Tkinter）
- 采用 Python 内置 Tkinter，无需本地 Web 服务
- 入口：`ui/tkinter/app.py`
- 启动脚本（macOS）：`startup/XJJ-Desktop.command`
- 启动脚本（Windows）：`startup/XJJ-Desktop.bat`
- 打包：`startup/Build-XJJ-Desktop-App.command` 使用 PyInstaller 生成 `dist/XJJ-Housekeeper.app`
- 图标：可将 `.icns` 文件放置到 `assets/icons/xjj.icns`，打包时自动识别

## 📋 系统要求

- **Python 3.8+** - 系统预装或自行安装
- **macOS 10.15+** - 支持现代macOS特性
- **Windows 10+** - 通过 `startup/XJJ-Desktop.bat` 启动原生 Tkinter 客户端
- **网络连接** - 首次运行时安装依赖

## 🔧 故障排除

### 常见问题

#### 1. "需要Python3"
- 确保已安装Python 3.8或更高版本
- 访问 https://www.python.org 下载安装

#### 2. 应用启动失败
- 检查网络连接（首次运行需要）
- 确保端口8501未被占用
- 重启应用尝试重新安装依赖

#### 3. 窗口空白
- 使用浏览器版本替代
- 检查控制台错误信息

### 手动安装依赖
如果自动安装失败，可手动安装（Poetry）：
```bash
poetry install
poetry run python -m streamlit run ui/app.py --server.port 8501
```

## 🎯 使用建议

- **首次使用**: 推荐浏览器版本，确保稳定运行
- **日常使用**: 桌面窗口版本，体验更佳
- **开发调试**: 浏览器版本，便于开发者工具使用

## 📱 启动相关结构

```
startup/
├── README.md              # 本文档
├── XJJ-Browser.command    # 浏览器版启动脚本（调用 `streamlit run ui/app.py`）
├── XJJ-Desktop.command    # macOS 桌面版启动脚本（原生 Tkinter 客户端）
└── XJJ-Desktop.bat        # Windows 桌面版启动脚本（原生 Tkinter 客户端）

## 🔄 与 UI 目录的关系

- Streamlit UI 代码位于 `ui/streamlit/` 子目录；原生桌面客户端位于 `ui/tkinter/`。
- 兼容入口 `ui/app.py` 作为薄包装，继续支持浏览器版本。
- 桌面版通过 `startup/XJJ-Desktop.command`（macOS）或 `startup/XJJ-Desktop.bat`（Windows）启动 Tkinter 客户端。
```

---

**💡 提示**: 两个启动脚本都会自动处理依赖安装，无需手动配置环境！