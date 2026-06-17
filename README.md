# `ngxtop` - **real-time** metrics for nginx server (and others)

**ngxtop** parses your nginx access log and outputs useful, `top`-like, metrics of your nginx server.
So you can tell what is happening with your server in real-time.

> `ngxtop` is designed to run for a short period of time, just like the `top` command, for troubleshooting and
> monitoring your nginx server at the moment. If you need a long-running monitoring process or want to store your
> webserver stats in an external monitoring / graphing system, consider a dedicated solution instead.

`ngxtop` tries to determine the correct location and format of the nginx access log file by default, so you can just
run `ngxtop` and have a close look at all requests coming to your nginx server. But it does not limit you to nginx and
the default top view. `ngxtop` is flexible enough for you to configure and change most of its behaviours. You can query
for different things, specify your log and format, and even parse a remote Apache common access log with ease.

This fork additionally supports:

- **Caddy JSON access logs** (`-f caddy`)
- **Generic flat-JSON access logs** (`-f json`), e.g. nginx configured with `log_format ... escape=json`
- **Log rotation handling** in follow mode (inode change / file truncation / `SIGHUP`)

See the sample usages below for ideas about what you can do with it.

## Installation

This project is packaged with a standard `pyproject.toml`. Install it (and its runtime dependencies
`docopt`, `tabulate`, `pyparsing`) from source in editable mode:

```bash
# with uv
uv pip install -e .

# or with pip
pip install -e .
```

This installs the `ngxtop` console command.

> **Python support:** historically `ngxtop` targeted Python 2 and 3. Note that the newer code paths in this fork
> (follow / log-rotation handling and the JSON parsers) use f-strings, which require **Python 3.6+**.

## Usage

```
Usage:
    ngxtop [options]
    ngxtop [options] (print|top|avg|sum) <var> ...
    ngxtop info
    ngxtop [options] query <query> ...

Options:
    -l <file>, --access-log <file>  access log file to parse.
    -f <format>, --log-format <format>  log format as specified in the log_format directive. [default: combined]
                                        Supported values: combined, common, caddy (Caddy JSON),
                                        json (generic flat-JSON / nginx escape=json)
    --no-follow  ngxtop default behavior is to ignore current lines in the log and only watch for new lines
                 as they are written to the access log. Use this flag to tell ngxtop to process the current
                 content of the access log instead.
    -t <seconds>, --interval <seconds>  report interval when running in follow mode [default: 2.0]

    -g <var>, --group-by <var>  group by variable [default: request_path]
    -w <var>, --having <expr>  having clause [default: 1]
    -o <var>, --order-by <var>  order of output for default query [default: count]
    -n <number>, --limit <number>  limit the number of records included in report for top command [default: 10]
    -a <exp> ..., --a <exp> ...  add exp (must be an aggregation exp: sum, avg, min, max, etc.) to output

    -v, --verbose  more verbose output
    -d, --debug  print every line and parsed record
    -h, --help  print this help message.
    --version  print version information.

    Advanced / experimental options:
    -c <file>, --config <file>  allow ngxtop to parse the nginx config file for log format and location.
    -i <filter-expression>, --filter <filter-expression>  filter in; records satisfying the given expression are processed.
    -p <filter-expression>, --pre-filter <filter-expression>  in-filter expression to check in the pre-parsing phase.
```

### How fields and filters work

Each parsed log record becomes a row in an in-memory SQLite table, and every field of the record becomes a column you
can use in `--group-by`, `--filter`, `--order-by` and `--having`.

- `--filter` / `-i` is a **Python expression** evaluated against each record, so the field names are available as
  variables and you can use any valid Python expression (comparisons, string methods, slicing, etc.).
- Derived fields are always available: `status_type` (2 / 3 / 4 / 5 for 2xx…5xx) and `request_path` (the path part of
  the request URI, query string stripped).

## Samples

### Default output

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

### View top source IPs of clients

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

### List 4xx or 5xx responses together with HTTP referer

```
$ ngxtop -i 'status >= 400' print request status http_referer
```

### Parse apache log from a remote server with the `common` format

```
$ ssh user@remote_server tail -f /var/log/apache2/access.log | ngxtop -f common
```

### Parse a Caddy server access log (JSON)

```
$ ngxtop -l /var/log/caddy/access.log -f caddy
```

## Working with flat-JSON access logs (`-f json`)

Use `-f json` for access logs where **each line is a single flat JSON object**, such as nginx configured with
`escape=json`:

```nginx
log_format json escape=json
  '{"remote_addr":"$remote_addr","logtime":"$time_local","domain":"$host",'
  '"req_method":"$request_method","req_uri":"$request_uri","status":$status,'
  '"bytes_sent":$body_bytes_sent,"req_time":$request_time,"ts":$msec}';

access_log /var/log/nginx/access.json.log json;
```

All original JSON keys are passed through unchanged, so any field (`domain`, `auth_user`, `upstream_status`,
`request_id`, …) can be used directly in `--group-by` / `--filter`. The canonical fields the default report relies on
are derived automatically, using these aliases when not already present:

| Canonical field | Source aliases (first match wins)           |
|-----------------|---------------------------------------------|
| `request_path`  | `request_uri`, `req_uri`, `uri`             |
| `request`       | `<method> <uri>` from `request_method` / `req_method` / `method` + URI |
| `bytes_sent`    | `bytes_sent`, `body_bytes_sent`, `size`     |
| `request_time`  | `request_time`, `req_time`, `duration`      |
| `status_type`   | derived from `status` (`status // 100`)     |

Malformed / non-JSON lines are skipped with a warning.

### Default view over a JSON log

```
$ ngxtop -f json -l access.json.log --no-follow
running for 0 seconds, 656 records processed

Summary:
|   count |   avg_bytes_sent |   2xx |   3xx |   4xx |   5xx |
|---------+------------------+-------+-------+-------+-------|
|     656 |        16542.848 |   553 |   103 |     0 |     0 |
```

### Group / filter by any original JSON field

Because every JSON key is preserved, you can group or filter on fields that are not part of the standard nginx set:

```bash
# top status codes
$ ngxtop -f json -l access.json.log --no-follow top status

# group by an arbitrary field (e.g. the upstream host / virtual domain)
$ ngxtop -f json -l access.json.log --no-follow -g domain

# redirects (3xx) broken down by domain
$ ngxtop -f json -l access.json.log --no-follow -g domain -i 'status >= 300 and status < 400'
```

### Average latency of a specific endpoint

```bash
$ ngxtop -f json -l access.json.log --no-follow avg request_time \
    -i 'request_path == "/push/push-api/logs"'

average ['request_time']
|   avg(request_time) |
|---------------------|
|               2.296 |
```

You can split the distribution with extra filters, e.g. how many calls were slower than 1 second:

```bash
$ ngxtop -f json -l access.json.log --no-follow avg request_time \
    -i 'request_path == "/push/push-api/logs" and request_time > 1'
```

## Filtering by time range

Since `--filter` is a plain Python expression, you can restrict analysis to a time window in two ways.

### By epoch timestamp (recommended, format-independent)

If your log has a numeric epoch field (e.g. `ts` in seconds), compute the boundaries and compare numerically. This is
robust and works across day boundaries:

```bash
# 2026-06-17 11:00:00 .. 11:10:00 (+08:00)
$ ngxtop -f json -l access.json.log --no-follow \
    -i 'ts >= 1781665200.0 and ts < 1781665800.0'
```

### By the textual `logtime` field (single day, quick)

When `logtime` has the fixed nginx format `17/Jun/2026:11:21:17 +0800`, the `HH:MM:SS` part sits at a fixed position,
so you can slice it and compare as strings (zero-padded time strings sort chronologically):

```bash
# 11:00:00 <= time < 11:10:00
$ ngxtop -f json -l access.json.log --no-follow \
    -i 'logtime[12:20] >= "11:00:00" and logtime[12:20] < "11:10:00"'

# minute-level: logtime[12:17] -> "11:00" .. "11:10"
```

`logtime[12:20]` is a Python string slice that extracts characters at index 12–19 (the `HH:MM:SS` portion):

```
17/Jun/2026:11:21:17 +0800
            ^^^^^^^^
            12     19
```

> **Note:** the `logtime` slice approach only compares the *time of day*, so it is correct only within a single day and
> relies on the fixed date width (`DD/Mon/YYYY`). For logs spanning multiple days, or to be format-independent, prefer
> the numeric `ts` comparison.

## Development

Run the test suite with `pytest` from the project root:

```bash
uv pip install -e . pytest
pytest
```

Tests live under `tests/`, with sample logs in `tests/fixtures/` (e.g. `caddy_sample.log`, `json_sample.log`).

## License

MIT — see [LICENSE.txt](LICENSE.txt).
