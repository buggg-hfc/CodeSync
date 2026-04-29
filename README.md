# CodeSync

将远程 Ubuntu 服务器上的代码自动同步到本地 Windows 机器的桌面 GUI 工具。

## 功能特性

- **SSH/SFTP 连接** — 支持密码和 SSH 密钥认证，凭据存储在系统凭据管理器（Windows Credential Manager）
- **多种同步触发方式** — 手动触发、定时自动同步、本地目录变化监控
- **双向同步** — 默认服务器 → 本地，可选双向（服务器优先冲突策略）
- **排除规则** — 支持 `.gitignore` 语法（`.git/`、`*.pyc`、`node_modules/` 等）
- **换行符转换** — 可选将 LF 转换为 CRLF（Windows 风格）
- **多配置管理** — 同时管理多个服务器配置，一键切换
- **系统托盘** — 最小化到托盘，支持快捷同步菜单
- **实时日志** — 内置日志查看器，同步历史一目了然

## 环境要求

- 本地：Windows 10/11，Python 3.11+
- 远程：Ubuntu（任意版本），已启用 SSH 服务

## 安装

```bash
git clone https://github.com/buggg-hfc/CodeSync.git
cd CodeSync
pip install -r requirements.txt
```

## 使用

```bash
python -m codesync.main
```

启动时最小化到托盘：

```bash
python -m codesync.main --minimized-to-tray
```

## 快速上手

1. 点击左侧 **＋ 新建** 创建服务器配置
2. 填写主机地址、用户名、认证方式（密钥或密码）
3. 在「同步」标签页填写远程目录和本地目录
4. 点击 **测试连接** 验证 SSH 连通性
5. 点击 **立即同步** 开始同步，或配置定时/监控触发

配置文件保存在 `%APPDATA%\codesync\config.json`，日志位于 `%APPDATA%\codesync\codesync.log`。

## 项目结构

```
codesync/
├── core/           # 业务逻辑（无 Qt 依赖）
│   ├── ssh_client.py       # SSH/SFTP 连接与文件传输
│   ├── sync_engine.py      # diff 算法、传输编排
│   ├── scheduler.py        # 定时触发（APScheduler）
│   ├── file_watcher.py     # 本地目录监控（watchdog）
│   └── exclusion_filter.py # .gitignore 排除规则（pathspec）
├── config/         # 配置读写
│   ├── models.py           # 数据模型（dataclass）
│   └── config_manager.py   # JSON 原子读写 + keyring 凭据
├── gui/            # PyQt6 界面
│   ├── main_window.py      # 主窗口
│   ├── profile_dialog.py   # 新建/编辑配置对话框
│   ├── sync_tab.py         # 同步控制与进度
│   ├── log_tab.py          # 实时日志
│   ├── settings_tab.py     # 全局设置
│   ├── tray_icon.py        # 系统托盘
│   └── widgets/            # 可复用控件
├── workers/        # QThread 工作线程
│   ├── sync_worker.py      # 执行同步
│   └── connection_worker.py# 测试连接
├── utils/
│   ├── constants.py        # 路径、默认值常量
│   └── logger.py           # 日志配置（文件 + 内存环形缓冲）
└── assets/         # 托盘图标
```

## 打包分发

使用 PyInstaller 打包为独立 Windows 可执行文件：

```bash
pip install pyinstaller
pyinstaller --name CodeSync --windowed --onefile \
  --icon codesync/assets/idle.png \
  --add-data "codesync/assets;codesync/assets" \
  --hidden-import keyring.backends.Windows \
  codesync/main.py
```

生成的 `dist/CodeSync.exe` 无需 Python 环境即可运行。

## 主要依赖

| 依赖 | 用途 |
|------|------|
| PyQt6 | GUI 框架 |
| paramiko | SSH/SFTP 连接 |
| watchdog | 本地目录文件变化监控 |
| APScheduler | 定时同步调度 |
| pathspec | .gitignore 语法排除规则 |
| keyring | 操作系统凭据安全存储 |

## 运行测试

```bash
pip install pytest pytest-mock
pytest tests/ -v
```

## License

MIT
