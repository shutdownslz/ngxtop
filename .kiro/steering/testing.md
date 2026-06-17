# 测试规范

## 框架与运行
- 使用 `pytest`。运行前确保依赖已装好（建议 `pip install -e .` 安装项目本身 + `pip install pytest`）。
- 在项目根目录运行：`pytest`（或 `pytest -v` 看详细，`pytest tests/test_parse_log.py` 跑单个文件）。

## 测试组织
- 测试统一放在 `tests/`，文件名以 `test_` 开头，函数名以 `test_` 开头。
- 样例日志等测试数据放在 `tests/fixtures/`（如 `caddy_sample.log`）。新增格式/场景时优先复用或新增 fixture，而不是在测试里硬编码大段日志字符串。
- 现有测试覆盖：日志解析（`test_parse_log.py`）、nginx config 解析（`test_config_parser.py`）、日志轮转（`test_log_rotation.py`）、Caddy 集成（`test_caddy_integration.py`）、JSON 提取（`test_json_extraction_fix.py`、`test_debug_json_parsing.py`）。

## 何时写测试
- 新增或修改**解析逻辑**（正则/JSON/config 解析、字段提取）必须配套测试，覆盖正常、异常和边界输入。
- 新增或修改**查询/聚合逻辑**（SQLite 查询、`status_type` 等派生字段）需验证 SQL 行为与输出。
- 修 bug 时先写一个能复现该 bug 的失败测试，再修复，确保回归被守住。

## 约定
- 测试应可独立运行、不依赖外部 nginx/Caddy 进程或真实日志文件；需要真实文件时用 `tmp_path` 等临时目录而非写死路径。
- 涉及 `follow()` / 日志轮转的测试要清理创建的临时文件，避免污染工作区。
- 提交改动前确保 `pytest` 全绿。
