# 编码规范

## 命名与风格
- 命名用 `snake_case`（函数、变量），常量用 `UPPER_CASE`（如 `LOG_FORMAT_COMBINED`、`DEFAULT_QUERIES`）。
- 内部/私有辅助函数以下划线开头（如 `_should_reopen_file`、`_sighup_handler`）。
- 遵循 PEP 8；保持与同文件已有代码一致的缩进和空行风格。

## 文档与注释
- 公共函数写 docstring，使用现有的 reStructuredText 风格：`:param x:` / `:return:`。
- 注释只解释非显然的逻辑（如日志轮转的 inode/大小判定、Py2/3 兼容分支），不要为显而易见的代码加注释。

## 错误处理
- 面向用户的致命错误统一走 `utils.error_exit(msg)`，它写 stderr 并以非零状态退出；不要直接散落 `sys.exit` 或裸 `print` 到 stderr。
- 文件/IO 操作要捕获 `OSError`/`IOError` 并按需重试（参考 `_open_file_with_retry` 的指数退避模式）。

## Python 2/3 兼容性（重要，当前不一致）
- `setup.py` 声明支持 Python 2.6/2.7 与 3.x，代码中也存在兼容写法：`from __future__ import print_function`、`try: import urlparse / except: import urllib.parse`、`choose_one` 里对 `sys.version` 的判断。
- **但** `ngxtop/ngxtop.py` 的较新代码（如 `follow()` 及其辅助函数）使用了 f-string，这是 Python 3.6+ 语法，已破坏 Py2 兼容。
- 改动前先与维护者确认目标：
  - 若决定**只支持 Python 3**：清理 `__future__`、`urlparse` 兼容分支和 `sys.version` 判断，并更新 `setup.py` 的 classifiers / `python_requires`。
  - 若仍要**保留 Py2 兼容**：禁止使用 f-string，改用 `%` 或 `.format()`，并修掉现有 f-string。
- 在该问题明确前，新代码避免引入新的 Py3-only 语法。

## 依赖
- 运行时依赖限定为已声明的 `docopt`、`tabulate`、`pyparsing`；新增依赖需先与维护者确认，并固定/同步到 `setup.py`。
