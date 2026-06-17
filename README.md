# `ngxtop` —— nginx 服务器（及其他）的**实时**指标工具

**ngxtop** 解析你的 nginx 访问日志，输出类似 `top` 的实用指标，让你实时了解服务器正在发生什么。

> `ngxtop` 的设计定位和 `top` 命令一样，用于**短时间**的排障与即时监控。如果你需要长期运行的监控进程，或想把 Web
> 服务器的统计数据存入外部监控 / 绘图系统，请考虑使用专门的方案。

`ngxtop` 默认会尝试自动确定 nginx 访问日志的位置和格式，所以你直接运行 `ngxtop` 就能查看所有进入服务器的请求。但它并不
局限于 nginx 和默认视图——`ngxtop` 足够灵活，绝大多数行为都可配置：你可以查询不同维度、指定自己的日志和格式，甚至轻松解析
远程 Apache 的 common 访问日志。

本 fork 在原版基础上额外支持：

- **Caddy JSON 访问日志**（`-f caddy`）
- **通用扁平 JSON 访问日志**（`-f json`），例如 nginx 配置 `log_format ... escape=json`
- follow 模式下的**日志轮转处理**（inode 变化 / 文件截断 / `SIGHUP`）

更多用法见下方示例。

## 安装

本项目使用标准的 `pyproject.toml` 打包，无需 `setup.py`。`pip`、`setuptools`、`build`、PyPI 都直接读取
`pyproject.toml`。安装后会生成 `ngxtop` 命令行工具，运行时依赖 `docopt`、`tabulate`、`pyparsing` 会自动安装。

下面任选一种方式安装：

### 1. 直接从 Git 安装（最方便，无需传文件）

```bash
pip install git+https://github.com/shutdownslz/ngxtop.git
# 或使用 SSH
pip install git+ssh://git@github.com/shutdownslz/ngxtop.git
# 指定分支 / 标签：在末尾加 @master 或 @v0.1.0
```

### 2. 安装预构建的 wheel（发给同学直接用）

仓库 `dist/` 目录下提供了已构建的安装包，下载后直接安装：

```bash
pip install dist/ngxtop-0.1.0-py2.py3-none-any.whl
```

### 3. 从源码安装

```bash
pip install .            # 普通安装
pip install -e .         # 可编辑模式（开发用）
# 也可使用 uv：uv pip install -e .
```

### 自行构建分发包

```bash
uv build        # 或 python -m build
# 产物输出到 dist/：ngxtop-<version>-py2.py3-none-any.whl 和 ngxtop-<version>.tar.gz
```

> **Python 版本支持：** `ngxtop` 历史上同时面向 Python 2 和 3。注意本 fork 中较新的代码路径（follow / 日志轮转处理，
> 以及 JSON 解析器）使用了 f-string，需要 **Python 3.6+**。

## 用法

> 完整的命令行参考（所有子命令、选项、字段、过滤与已知限制）见 [docs/cli.md](docs/cli.md)。

```
Usage:
    ngxtop [options]
    ngxtop [options] (print|top|avg|sum) <var> ...
    ngxtop info
    ngxtop [options] query <query> ...

Options:
    -l <file>, --access-log <file>  要解析的访问日志文件。
    -f <format>, --log-format <format>  log_format 指令中指定的日志格式。[default: combined]
                                        可选值：combined、common、caddy（Caddy JSON）、
                                        json（通用扁平 JSON / nginx escape=json）
    --no-follow  ngxtop 默认会忽略日志中已有的行，只监视后续新写入的行。
                 使用此标志可让 ngxtop 改为处理访问日志的当前内容。
    -t <seconds>, --interval <seconds>  follow 模式下的报告刷新间隔 [default: 2.0]

    -g <var>, --group-by <var>  分组字段 [default: request_path]
    -w <var>, --having <expr>  having 子句 [default: 1]
    -o <var>, --order-by <var>  默认查询的输出排序 [default: count]
    -n <number>, --limit <number>  top 命令报告中包含的记录条数上限 [default: 10]
    -a <exp> ..., --a <exp> ...  向输出中添加聚合表达式（须为 sum、avg、min、max 等聚合表达式）

    -v, --verbose  更详细的输出。
    -d, --debug  打印每一行及其解析后的记录。
    -h, --help  显示帮助信息。
    --version  显示版本信息。

    高级 / 实验性选项：
    -c <file>, --config <file>  允许 ngxtop 解析 nginx 配置文件以获取日志格式和位置。
    -i <filter-expression>, --filter <filter-expression>  过滤表达式；只处理满足该表达式的记录。
    -p <filter-expression>, --pre-filter <filter-expression>  预解析阶段的过滤表达式。
```

### 字段与过滤的工作方式

每条解析出的日志记录会成为内存 SQLite 表中的一行，记录的每个字段都会成为一列，可用于 `--group-by`、`--filter`、
`--order-by` 和 `--having`。

- `--filter` / `-i` 是一个针对每条记录求值的 **Python 表达式**，因此字段名可作为变量使用，你可以使用任意合法的 Python
  表达式（比较、字符串方法、切片等）。
- 始终可用的派生字段：`status_type`（2 / 3 / 4 / 5 分别对应 2xx…5xx）和 `request_path`（请求 URI 的路径部分，已去掉
  查询串）。

## 示例

### 默认输出

```
$ ngxtop
running for 411 seconds, 64332 records processed: 156.60 req/sec

Summary:
|   count |   avg_bytes_sent |   2xx |   3xx |   4xx |   5xx |
|---------+------------------+-------+-------+-------+-------|
|   64332 |         2775.251 | 61262 |  2994 |    71 |     5 |

Detailed:
| request_path             |   count |   avg_bytes_sent |   2xx |   3xx |   4xx |   5xx |
|--------------------------+---------+------------------+-------+-------+-------+-------|
| /abc/xyz/xxxx            |   20946 |          434.693 | 20935 |     0 |    11 |     0 |
| /xxxxx.json              |    5633 |         1483.723 |  5633 |     0 |     0 |     0 |
| /static/js/utils.min.js  |    3031 |         1781.155 |  2104 |   927 |     0 |     0 |
```

### 查看客户端来源 IP 排行

```
$ ngxtop top remote_addr
running for 20 seconds, 3215 records processed: 159.62 req/sec

top remote_addr
| remote_addr     |   count |
|-----------------+---------|
| 118.173.177.161 |      20 |
| 110.78.145.3    |      16 |
| 171.7.153.7     |      16 |
```

### 列出 4xx / 5xx 响应及其 HTTP referer

```
$ ngxtop -i 'status >= 400' print request status http_referer
```

### 用 `common` 格式解析远程服务器的 Apache 日志

```
$ ssh user@remote_server tail -f /var/log/apache2/access.log | ngxtop -f common
```

### 解析 Caddy 服务器访问日志（JSON）

```
$ ngxtop -l /var/log/caddy/access.log -f caddy
```

## 处理扁平 JSON 访问日志（`-f json`）

当访问日志的**每一行都是一个扁平的 JSON 对象**时（例如 nginx 配置 `escape=json`），使用 `-f json`：

```nginx
log_format json escape=json
  '{"remote_addr":"$remote_addr","logtime":"$time_local","domain":"$host",'
  '"req_method":"$request_method","req_uri":"$request_uri","status":$status,'
  '"bytes_sent":$body_bytes_sent,"req_time":$request_time,"ts":$msec}';

access_log /var/log/nginx/access.json.log json;
```

所有原始 JSON 键都会原样保留，因此任意字段（`domain`、`auth_user`、`upstream_status`、`request_id` 等）都可以直接用于
`--group-by` / `--filter`。默认报告所依赖的规范字段会自动派生，当记录中不存在时按以下别名（取第一个命中的）推导：

| 规范字段        | 来源别名（取第一个命中）                    |
|-----------------|---------------------------------------------|
| `request_path`  | `request_uri`、`req_uri`、`uri`             |
| `request`       | 由 `request_method` / `req_method` / `method` + URI 拼成 `<method> <uri>` |
| `bytes_sent`    | `bytes_sent`、`body_bytes_sent`、`size`     |
| `request_time`  | `request_time`、`req_time`、`duration`      |
| `status_type`   | 由 `status` 派生（`status // 100`）         |

格式错误 / 非 JSON 的行会被跳过，并打印一条 warning。

### 对 JSON 日志的默认视图

```
$ ngxtop -f json -l access.json.log --no-follow
running for 0 seconds, 656 records processed

Summary:
|   count |   avg_bytes_sent |   2xx |   3xx |   4xx |   5xx |
|---------+------------------+-------+-------+-------+-------|
|     656 |        16542.848 |   553 |   103 |     0 |     0 |
```

### 按任意原始 JSON 字段分组 / 过滤

由于所有 JSON 键都被保留，你可以对不属于标准 nginx 字段集的字段进行分组或过滤：

```bash
# 状态码排行
$ ngxtop -f json -l access.json.log --no-follow top status

# 按任意字段分组（例如上游主机 / 虚拟域名）
$ ngxtop -f json -l access.json.log --no-follow -g domain

# 按域名拆分 3xx 重定向
$ ngxtop -f json -l access.json.log --no-follow -g domain -i 'status >= 300 and status < 400'
```

### 查看某个接口的平均耗时

```bash
$ ngxtop -f json -l access.json.log --no-follow avg request_time \
    -i 'request_path == "/push/push-api/logs"'

average ['request_time']
|   avg(request_time) |
|---------------------|
|               2.296 |
```

可以叠加过滤条件来拆分分布，例如有多少次调用慢于 1 秒：

```bash
$ ngxtop -f json -l access.json.log --no-follow avg request_time \
    -i 'request_path == "/push/push-api/logs" and request_time > 1'
```

## 按时间范围过滤

由于 `--filter` 就是普通的 Python 表达式，你可以用两种方式把分析限定在某个时间窗内。

### 按 epoch 时间戳（推荐，与格式无关）

如果日志中有数值型的 epoch 字段（例如以秒为单位的 `ts`），计算出边界后做数值比较即可。这种方式稳健，且能跨天正常工作：

```bash
# 2026-06-17 11:00:00 .. 11:10:00 （+08:00）
$ ngxtop -f json -l access.json.log --no-follow \
    -i 'ts >= 1781665200.0 and ts < 1781665800.0'
```

### 按文本 `logtime` 字段（单日、快捷）

当 `logtime` 为固定的 nginx 格式 `17/Jun/2026:11:21:17 +0800` 时，`HH:MM:SS` 部分位于固定位置，因此可以切片后按字符串
比较（零填充的时间字符串其字典序即时间先后）：

```bash
# 11:00:00 <= 时间 < 11:10:00
$ ngxtop -f json -l access.json.log --no-follow \
    -i 'logtime[12:20] >= "11:00:00" and logtime[12:20] < "11:10:00"'

# 精确到分钟：logtime[12:17] -> "11:00" .. "11:10"
```

`logtime[12:20]` 是 Python 字符串切片，取出索引 12–19 的字符（即 `HH:MM:SS` 部分）：

```
17/Jun/2026:11:21:17 +0800
            ^^^^^^^^
            12     19
```

> **注意：** `logtime` 切片方式只比较了**当天的时间**，因此仅在**单日**内正确，且依赖固定的日期宽度（`DD/Mon/YYYY`）。
> 对于跨天的日志，或想与格式无关，请优先使用数值型的 `ts` 比较。

## 计算 QPS 与峰值 QPS

下列示例都用 `query` 子命令，依赖日志中以秒为单位的数值 epoch 字段 `ts`（QPS 的计算本质上需要"按时间分桶"）。

### 平均 QPS（最近一小时）

窗口上下界直接在 SQL 里用 `max(ts)` 和 `max(ts)-3600` 算，QPS = 窗口内行数 / 3600：

```bash
$ ngxtop -f json -l access.json.log --no-follow query \
  'select count(1) as cnt, round(count(1)/3600.0, 4) as qps
   from log
   where ts >= (select max(ts) from log) - 3600'

|   cnt |   qps |
|-------+-------|
|   347 | 0.096 |
```

> 输出首行的 `... records processed` 是读入的总行数，**不是**窗口内的数；窗口内的数看结果表的 `cnt`。
> 这里取的是"日志最新时刻往前推一小时"，而非系统当前时间。

### 峰值 QPS（按整秒分桶取最大）

真实峰值 QPS = 任意 1 秒内的最大请求数，用 `cast(ts as integer)` 把时间截到整秒分桶再取 `max`：

```bash
$ ngxtop -f json -l access.json.log --no-follow query \
  'select max(c) as peak_qps from (select count(1) as c from log group by cast(ts as integer))'

|   peak_qps |
|------------|
|         57 |
```

定位峰值发生在哪一秒（顺便看 QPS 最高的前几秒，时间转北京时间）：

```bash
$ ngxtop -f json -l access.json.log --no-follow query \
  "select datetime(cast(ts as integer)+8*3600,'unixepoch') as sec_utc8, count(1) as qps
   from log group by cast(ts as integer) order by qps desc limit 5"

| sec_utc8            |   qps |
|---------------------+-------|
| 2026-06-17 10:34:55 |    57 |
| 2026-06-17 10:47:23 |    45 |
| 2026-06-17 10:19:18 |    26 |
```

> 平均 QPS 与峰值 QPS 可能差很多：上例平均仅 ~0.1 req/s，峰值却到 57 req/s，说明流量很**突发**。
> 想要按分钟峰值，把分桶键换成 `cast(ts/60 as integer)` 即可。

## 开发

在项目根目录用 `pytest` 运行测试：

```bash
uv pip install -e . pytest
pytest
```

测试位于 `tests/` 下，样例日志在 `tests/fixtures/`（如 `caddy_sample.log`、`json_sample.log`）。

## 许可证

MIT —— 见 [LICENSE.txt](LICENSE.txt)。
