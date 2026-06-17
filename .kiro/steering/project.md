# ngxtop 项目说明

## 概述
`ngxtop` 是一个命令行工具，解析 nginx（及兼容格式）的访问日志，输出类似 `top` 的实时指标，用于排障和监控。本仓库在原版 ngxtop 基础上扩展了 **Caddy JSON 日志格式** 支持和 **日志轮转（log rotation）处理**。

- 语言：Python（兼容 Python 2/3，代码中保留了 `from __future__ import print_function`、`urlparse`/`urllib.parse` 兼容写法）
- 入口命令：`ngxtop`（console_scripts → `ngxtop.ngxtop:main`）
- 打包：`setup.py`（setuptools），版本 `0.0.3`
- 运行时依赖：`docopt`、`tabulate`、`pyparsing`
- 许可证：MIT

## 工作原理
1. 通过 `docopt` 解析命令行参数（用法字符串在 `ngxtop/ngxtop.py` 顶部 docstring 中定义）。
2. 确定访问日志路径与日志格式：可由 `-l/--access-log` 和 `-f/--log-format` 显式指定，或通过 `-c/--config` 解析 nginx 配置自动检测。
3. 根据日志格式构建解析器：
   - nginx 文本格式 → 用正则表达式解析（`build_pattern`）。
   - `caddy` → 特殊分支，按 JSON 解析。
4. 将解析出的记录写入 **内存 SQLite** 表 `log`，用 SQL 完成聚合查询（见 `DEFAULT_QUERIES`）。
5. 用 `tabulate` 渲染输出；follow 模式下定时刷新（默认 2 秒）。

## 目录结构
- `ngxtop/ngxtop.py` —— 主程序：CLI、`follow()`（含日志轮转/inode 变更/SIGHUP 处理）、SQLite 查询处理、curses 输出、Caddy JSON 解析。
- `ngxtop/config_parser.py` —— 用 `pyparsing` 解析 nginx 配置中的 `access_log`/`log_format` 指令；`build_pattern`/`extract_variables` 构建解析模式；内置 combined/common/caddy 格式常量。
- `ngxtop/utils.py` —— 辅助函数 `choose_one`、`error_exit`。
- `tests/` —— pytest 测试：日志解析、config 解析、日志轮转、Caddy 集成、JSON 提取等；`tests/fixtures/` 含样例日志。

## 关键概念
- **日志格式**：支持 `combined`（默认）、`common`、`caddy`。combined/common 走正则，caddy 走 JSON。
- **字段/变量**：从日志格式中提取的字段成为 SQLite 列，可用于 `--group-by`、`--filter`、`--having`、`--order-by`。
- **status_type**：派生字段，按状态码分组为 2xx/3xx/4xx/5xx。
- **日志轮转**：`follow()` 通过 inode 变化、文件大小骤降以及 SIGHUP 信号检测轮转并重新打开文件，带重试与指数退避。

## 开发约定
- 改动需兼顾 Python 2/3 兼容性（除非明确决定放弃 Py2）。
- 新增/修改解析或查询逻辑时，需在 `tests/` 下补充或更新 pytest 测试，并复用 `tests/fixtures/` 中的样例日志。
- 测试运行：`pytest`（需先安装 `pytest` 及项目依赖，建议 `pip install -e .`）。
