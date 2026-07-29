# 自动巡检报告生成工具

基于 XML 数据自动下载、解析并生成 Word 巡检报告的工具，支持服务器巡检和数据库巡检两类报告。

## 功能特性

- **远程下载**：通过 rsync 从远程服务器同步巡检 XML 数据
- **报告生成**：解析 XML 数据，自动生成 `.doc` 格式的 Word 巡检报告
- **图表支持**：数据库报告包含磁盘、CPU、内存等 matplotlib 可视化图表
- **阈值检测**：服务器报告包含 21 项阈值检查及中文优化建议
- **本地清理**：支持一键清理本地 XML 历史数据

## 环境要求

- Python 3.x
- Windows 操作系统（内置 cwRsync 工具）
- **SimHei 字体**（用于 matplotlib 中文图表显示）

## 配置前必读

使用前必须替换代码中的占位符：

| 文件 | 需替换内容 | 说明 |
|------|-----------|------|
| `handler/remote_downloader.py` | `[yourpassword]`, `[user]@[server_ip]`（第 21-22 行） | rsync 密码和服务器地址 |
| `scripts/system_check_xml.sh` | `[user]@[server_ip]`（ssh/scp 目标） | 服务器采集脚本上传目标 |
| `scripts/ora_check_xml.sh` | `[user]@[server_ip]`（ssh/scp 目标） | 数据库采集脚本上传目标 |

服务器采集脚本部署在远程 Linux 服务器上运行，**不在本地执行**。详见下方"远程服务器要求"。

## 安装依赖

```bash
# 方式一：手动安装
pip install docxtpl matplotlib lxml

# 方式二：通过 requirements.txt 一键安装
pip install -r requirements.txt
```

### 依赖说明

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| docxtpl | >=0.20.0 | Word 模板渲染 |
| python-docx | >=1.1.0 | Word 文档操作 |
| matplotlib | >=3.5.0 | 数据图表生成 |
| lxml | >=4.9.0 | XML 解析 |

## 使用说明

### 启动程序

双击运行项目根目录下的启动脚本：

```bash
generate_report.bat
```

或在命令行中执行：

```bash
cd handler
python main_menu.py
```

> **注意**：所有 Python 脚本必须在 `handler/` 目录下运行，否则路径解析会出错。

### 菜单操作

启动后进入交互式菜单：

| 选项 | 功能 |
|------|------|
| 1 | 下载巡检文件 — 从远程服务器通过 rsync 同步最新 XML 数据 |
| 2 | 生成巡检报告 — 解析 XML 并生成 Word 巡检报告 |
| 3 | 删除本地旧文件 — 清理 `system_check/logs/` 和 `ora_check/logs/` 目录 |
| 0 | 退出程序 |

### 报告生成流程

1. 选择 **1** 下载远程 XML 数据（`system_check_<timestamp>.xml` 和 `ora_check_<timestamp>.xml`）
2. 选择 **2** 生成报告，程序将依次生成：
   - 服务器巡检报告（含 21 项阈值检查）
   - 数据库巡检报告（含磁盘/CPU/内存图表分析）
3. 报告保存至 `check_report/` 目录，文件名格式：`YYYY-MM<学校名><类型>巡检报告.doc`

## 项目结构

```
Autocheck/
├── handler/                      # Python 核心代码目录
│   ├── main_menu.py              # 交互式菜单入口
│   ├── scheduler.py              # 报告生成调度器
│   ├── remote_downloader.py      # rsync 远程下载模块
│   ├── local_cleaner.py          # 本地 XML 清理模块
│   ├── folder_handler.py         # 日志目录遍历与最新文件查找
│   ├── xml_handler.py            # XML 解析器（XPath）
│   ├── server_word_handler.py    # 服务器报告生成（21 项检查）
│   ├── database_word_handler.py  # 数据库报告生成（图表+分析）
│   ├── server_template.docx      # 服务器报告 Word 模板
│   └── database_template.docx    # 数据库报告 Word 模板
├── scripts/                      # 远程服务器采集脚本
│   ├── system_check_xml.sh       # 服务器信息采集脚本
│   └── ora_check_xml.sh          # 数据库信息采集脚本
├── cwRsync/                      # Windows 版 rsync 工具集
├── generate_report.bat           # Windows 启动脚本
├── requirements.txt              # Python 依赖列表
├── 先安装依赖.txt                 # 快速安装提示
└── README.md                     # 本文件
```

## 配置说明

### 远程服务器要求

- 远程服务器必须存在 `/etc/assetname` 文件，格式为：`学校名称-系统名称-IP地址`
- 采集脚本仅支持 **Anolis / CentOS / Ubuntu / RedHat / Oracle Linux** 系统
- 采集脚本需要 **root 权限** 执行
- `ora_check_xml.sh` 自动检测 Oracle 用户（优先 `oracle`，备用 `oracle12c`）
- 部署前需在远程服务器上配置 SSH 密钥（`/root/.ssh/id_rsa`），并将公钥添加到中转服务器的 `authorized_keys`（端口 8859）

### 端口说明

| 方向 | 协议 | 端口 | 用途 |
|------|------|------|------|
| 下载 | rsync | 8858 | 从远程服务器下载 XML 数据 |
| 上传 | SSH | 8859 | 向远程服务器上传文件 |

## 注意事项

1. **工作目录**：所有 Python 脚本必须在 `handler/` 目录下运行，使用相对路径访问 `../system_check/logs` 等目录。
2. **字体问题**：若图表中文显示为方框，请确保系统已安装 **SimHei（黑体）** 字体。
3. **报告格式**：输出报告为 `.doc` 格式（兼容旧版 Word），但内部使用 `.docx` 模板通过 `docxtpl` 生成。
4. **删除确认**：选项 3 的清理操作需要手动输入 `y` 确认，防止误删。
5. **生成顺序**：报告按 服务器 → 数据库 顺序生成，若任一环节失败会暂停并输出错误，不会继续后续步骤。
