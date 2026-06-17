# ngxtop 命令行帮助文档

`ngxtop` 解析 nginx（及兼容格式）访问日志，把每条记录写入**内存 SQLite 表 `log`**，再用 SQL 做聚合，最后用 `tabulate`
渲染成类似 `top` 的报表。理解这一点，就能理解几乎所有选项：**每个字段都是表里的一列，分组 / 过滤 / 排序本质上都是 SQL。**

---

## 1. 命令格式

```
ngxtop [options]                          # 默认报表（Summary + Detailed）
ngxtop [options] (print|top|avg|sum) <var> ...   # 子命令，作用于一个或多个字段
ngxtop info                               # 打印自动探测到的配置信息
ngxtop [options] query <query> ...        # 执行自定义 SQL（⚠ 当前不可用，见 §9）
```

`<var>` 可以是日志里的任意字段名，或派生字段 `status_type` / `request_path`（见 §5）。

---

## 2. 子命令详解

| 子命令 | 作用 | 示例 |
|--------|------|------|
| （无） | 默认报表：整体 Summary + 按 `--group-by` 分组的 Detailed 表 | `ngxtop` |
| `print <var>...` | 直接列出这些字段（按其组合去重分组） | `ngxtop print request status http_referer` |
| `top <var>...` | 每个字段各出一张"出现次数排行"表（降序，受 `--limit` 限制） | `ngxtop top remote_addr` |
| `avg <var>...` | 对这些字段求平均值 | `ngxtop avg request_time` |
| `sum <var>...` | 对这些字段求和 | `ngxtop sum bytes_sent` |
| `info` | 打印探测到的 nginx 配置文件、访问日志路径、日志格式、可用变量 | `ngxtop info` |
| `query <sql>...` | 执行自定义 SQL（表名为 `log`） | ⚠ 当前有 bug，见 §9 |

> 子命令都可叠加 `-i/--filter` 过滤、`-f/--log-format` 指定格式、`-l/--access-log` 指定文件。

---

## 3. 选项详解

### 基本

| 选项 | 含义 | 默认值 |
|------|------|--------|
| `-l <file>`, `--access-log <file>` | 要解析的访问日志文件。也可用管道从 stdin 输入（见 §8） | 自动探测 |
| `-f <format>`, `--log-format <format>` | 日志格式：`combined` / `common` / `caddy` / `json`（见 §4） | `combined` |
| `--no-follow` | 处理日志**当前已有内容**后退出；不加则进入 follow 模式持续监视新行 | 关闭（即默认 follow） |
| `-t <seconds>`, `--interval <seconds>` | follow 模式下报表刷新间隔（秒） | `2.0` |

### 查询塑形（作用于默认报表）

| 选项 | 含义 | 默认值 |
|------|------|--------|
| `-g <var>`, `--group-by <var>` | Detailed 表的分组字段 | `request_path` |
| `-w <expr>`, `--having <expr>` | SQL `HAVING` 子句，过滤分组后的结果 | `1`（不过滤） |
| `-o <var>`, `--order-by <var>` | 默认报表排序表达式（降序） | `count` |
| `-n <number>`, `--limit <number>` | 报表 / `top` 输出的最大行数 | `10` |
| `-a <exp> ...`, `--a <exp> ...` | 文档声明用于添加聚合表达式 ⚠ **当前无效，见 §9** | — |

### 调试与帮助

| 选项 | 含义 |
|------|------|
| `-v`, `--verbose` | 更详细输出（INFO 级日志） |
| `-d`, `--debug` | 打印每一行原文及解析后的记录（DEBUG 级） |
| `-h`, `--help` | 显示帮助 |
| `--version` | 显示版本 |

### 高级 / 实验性

| 选项 | 含义 |
|------|------|
| `-c <file>`, `--config <file>` | 解析指定 nginx 配置文件以自动获取日志路径与格式（见 §7） |
| `-i <expr>`, `--filter <expr>` | **解析后**按记录过滤的 Python 表达式（见 §6） |
| `-p <expr>`, `--pre-filter <expr>` | **解析前**按原始行字符串过滤的 Python 表达式（见 §6） |

---

## 4. 日志格式（`-f`）

| 值 | 说明 | 解析方式 |
|----|------|----------|
| `combined` | nginx 默认组合格式（含 referer、user-agent） | 正则 |
| `common` | Apache/nginx common 格式 | 正则 |
| `caddy` | Caddy 服务器的嵌套 JSON 访问日志 | JSON（要求顶层 `request` 对象） |
| `json` | **通用扁平 JSON**：每行一个 JSON 对象，例如 nginx `escape=json` | JSON（透传全部键 + 派生规范字段） |

### `combined` / `common`（正则）
可用字段就是格式串里的变量，如 `remote_addr`、`remote_user`、`time_local`、`request`、`status`、`body_bytes_sent`、
`http_referer`、`http_user_agent` 等。

### `json`（通用扁平 JSON）
所有原始 JSON 键**原样保留**，可直接用于 `-g` / `-i`。默认报表依赖的规范字段在缺失时按别名自动派生：

| 规范字段 | 来源别名（取第一个命中） |
|----------|--------------------------|
| `request_path` | `request_uri` / `req_uri` / `uri` |
| `request` | 由 `request_method`(`/req_method`/`method`) + URI 拼成 `<method> <uri>` |
| `bytes_sent` | `bytes_sent` / `body_bytes_sent` / `size` |
| `request_time` | `request_time` / `req_time` / `duration` |
| `status_type` | 由 `status` 派生（`status // 100`） |

非 JSON / 格式错误的行会被跳过并打印 warning。

---

## 5. 字段与派生列

- 每条记录的每个字段 = SQLite 表 `log` 的一列，可用于 `-g`、`-i`、`-o`、`-w` 以及 `print/top/avg/sum` 的 `<var>`。
- **始终可用的派生字段**：
  - `status_type`：状态码整除 100，即 `2`/`3`/`4`/`5` 对应 2xx/3xx/4xx/5xx。
  - `request_path`：请求 URI 的路径部分（已去掉 `?` 后的查询串）。
- 数值字段（`status`、`bytes_sent`、`request_time`）会被转成数值类型，可直接做大小比较和聚合。

查看某份日志到底有哪些可用字段：

```bash
ngxtop info           # 配置自动探测模式下，列出 available variables
ngxtop -d --no-follow -l <file> -f <fmt> | head   # 用 -d 看每条解析后的记录
```

---

## 6. 过滤

### `-i` / `--filter`（解析后，按记录）
是一个对**每条记录**求值的 **Python 表达式**，字段名作为变量；返回真值的记录才被统计。支持任意合法 Python 表达式：

```bash
# 只看 4xx/5xx
ngxtop -i 'status >= 400'

# 字符串方法
ngxtop avg bytes_sent -i 'status == 200 and request_path.startswith("/api")'

# 任意原始字段（json 格式透传）
ngxtop -f json -i 'domain == "a.example.com" and upstream_status == "200"'
```

### `-p` / `--pre-filter`（解析前，按原始行）
在解析之前对**原始行字符串**求值，变量名是 `line`。用于在昂贵的解析前先粗筛，提升性能：

```bash
ngxtop -p '"GET" in line'
```

### 按时间范围过滤
`--filter` 是普通 Python 表达式，因此有两种写法（详见 README 的"按时间范围过滤"）：

```bash
# 推荐：数值 epoch 字段，跨天稳健、与格式无关
ngxtop -f json -i 'ts >= 1781665200.0 and ts < 1781665800.0'

# 快捷：对固定格式的 logtime 做字符串切片（仅单日有效）
#   logtime 形如 17/Jun/2026:11:21:17 +0800，HH:MM:SS 在索引 [12:20]
ngxtop -f json -i 'logtime[12:20] >= "11:00:00" and logtime[12:20] < "11:10:00"'
```

> ⚠ 安全提示：`-i` / `-p` 内部用 `eval` 执行，**只应传入你自己可信的表达式**，不要把不可信内容拼进去。

---

## 7. 配置自动探测（`-c`）与默认行为

- 不指定 `-l` 时，ngxtop 会尝试解析 nginx 配置（可用 `-c` 指定配置文件）以获得访问日志路径和 `log_format`。
- 当 stdin 是管道时，自动从 stdin 读取（见 §8）。
- `ngxtop info` 会打印探测结果，便于排查"没找到日志/格式不对"的问题。

---

## 8. follow 模式、stdin 与日志轮转

- **默认 follow**：像 `tail -f`，只统计启动后新写入的行，按 `--interval` 周期刷新报表（curses 界面）。
- **`--no-follow`**：处理当前文件内容后直接打印一次结果并退出，适合离线分析单个文件。
- **stdin 管道**：

  ```bash
  ssh remote tail -f /var/log/apache2/access.log | ngxtop -f common
  ```

- **日志轮转**：follow 模式下通过 inode 变化、文件大小骤降及 `SIGHUP` 信号检测轮转并自动重新打开文件（带重试与指数退避）。

---

## 9. 已知限制 / 注意事项

- **`query` 子命令当前不可用**：代码引用了用法字符串里未定义的 `<fields>`，会抛 `KeyError`。自定义聚合请暂时用
  `print/top/avg/sum` + `-g/-w/-o` 组合替代。
- **`-a` / `--a` 当前无效**：选项虽在帮助中列出，但代码未使用，传了不会生效。
- **`logtime` 切片过滤仅单日有效**：只比较了当天时间，且依赖固定日期宽度 `DD/Mon/YYYY`；跨天请用数值 `ts`。
- **Python 版本**：较新代码路径（follow / 日志轮转 / JSON 解析）使用 f-string，需 **Python 3.6+**。

---

## 10. 默认报表的 SQL（理解 `-g/-w/-o/-n`）

默认报表由两条 SQL 生成，`-g/-w/-o/-n` 直接填进模板：

**Summary（整体）**
```sql
SELECT count(1) AS count, avg(bytes_sent) AS avg_bytes_sent,
       count(CASE WHEN status_type=2 THEN 1 END) AS '2xx',
       count(CASE WHEN status_type=3 THEN 1 END) AS '3xx',
       count(CASE WHEN status_type=4 THEN 1 END) AS '4xx',
       count(CASE WHEN status_type=5 THEN 1 END) AS '5xx'
FROM log ORDER BY <--order-by> DESC LIMIT <--limit>
```

**Detailed（分组）**
```sql
SELECT <--group-by>, count(1) AS count, avg(bytes_sent) AS avg_bytes_sent,
       count(CASE WHEN status_type=2 THEN 1 END) AS '2xx', ... '5xx'
FROM log
GROUP BY <--group-by>
HAVING <--having>
ORDER BY <--order-by> DESC
LIMIT <--limit>
```

因此 `-o` 可以写聚合表达式，例如按总流量排序：

```bash
ngxtop --order-by 'avg(bytes_sent) * count'
```

---

## 11. 常用示例速查

```bash
# 默认 top 视图（自动探测配置）
ngxtop

# 离线分析一个文件
ngxtop --no-follow -l /var/log/nginx/access.log

# 状态码为 404 的路径排行
ngxtop top request_path -i 'status == 404'

# 谁请求最多
ngxtop --group-by remote_addr

# 列出 4xx/5xx 的请求、状态、referer
ngxtop -i 'status >= 400' print request status http_referer

# 路径以 /foo 开头的 200 响应的平均响应体大小
ngxtop avg bytes_sent -i 'status == 200 and request_path.startswith("/foo")'

# 远程 Apache common 日志
ssh remote tail -f /var/log/apache2/access.log | ngxtop -f common

# Caddy JSON 日志
ngxtop -l /var/log/caddy/access.log -f caddy

# 通用扁平 JSON：按域名拆分 3xx
ngxtop -f json -l access.json.log --no-follow -g domain -i 'status >= 300 and status < 400'

# 通用扁平 JSON：某接口平均耗时
ngxtop -f json -l access.json.log --no-follow avg request_time -i 'request_path == "/api/x"'
```

---

更完整的安装与场景说明见 [README.md](../README.md)。
