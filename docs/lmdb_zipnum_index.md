# LMDB ZipNum secondary index (PoC)

Proof of concept of [arquivo/pwa-technologies#1675](https://github.com/arquivo/pwa-technologies/issues/1675):
read the secondary index (`.idx`) of a ZipNum CDX index from an [LMDB](http://www.lmdb.tech/doc/)
database, instead of pywb's binary search over the `.idx` file.

| | `.idx` file | LMDB `.idx` |
|---|---|---|
| index source | `ZipNumIndexSource` (pywb) | [`LMDBZipNumIndexSource`](../pywb_arquivo/lmdb_zipnum.py) |
| `.idx` lookup | open the file, binary search over 8 KiB blocks, read lines | B+tree cursor on a memory map |
| shards and `.loc` | | the same, unchanged |

Only the lookups on the `.idx` change. pywb's own `ZipNumIndexSource` code runs with its `.idx` file
functions (`open`, `search`, `iter_range` and `read_last_line`) replaced by LMDB cursor versions, so the
pages, the blocks of the shards and the CDX lines are computed by pywb as with the `.idx` file.
The CDX lines stay on the shards, and pagination and `max_blocks` don't change.

## Configuration

Add the LMDB database to a `zipnum` index of the pywb `config.yaml`:

```yaml
collections:
  wayback:
    index:
      type: zipnum
      path: /data/indexes_cdx/RAQ2019/RAQ2019.idx
      lmdb: lmdb:///data/indexes_cdx/idx.lmdb?db=RAQ2019
```

* `path` is still needed: the `.loc` file next to it locates the shards, and the `.idx` file is used
  when LMDB isn't available.
* A single LMDB environment (a directory with `data.mdb` and `lock.mdb`) can have one named database
  per ZipNum, and also the [path index](lmdb_path_index.md) databases.
* A missing environment or named database, or a failed lookup, is logged and the `.idx` file is used
  instead; LMDB is opened again after 60 seconds.

The `lmdb` option is added to pywb by the [`pywb_arquivo.wayback`](../pywb_arquivo/wayback.py) WSGI
application, used by the `framed` and `unframed` `uwsgi.ini`. Like the LMDB path index, the environment
is opened read only on the first lookup of each uWSGI worker, and pywb needs write access to its
`lock.mdb`. docker compose mounts `CDX_FOLDER` (default: `/data/indexes_cdx`) on `/data/indexes_cdx`.

## Loading the `.idx`

[`pywb_arquivo/lmdb_zipnum_index.py`](../pywb_arquivo/lmdb_zipnum_index.py) loads a `.idx` file into a
named database, creating the environment if needed:

```bash
# load the .idx of a ZipNum into a new database
python -m pywb_arquivo.lmdb_zipnum_index load --env /data/indexes_cdx/idx.lmdb --db RAQ2019 \
    /data/indexes_cdx/RAQ2019/RAQ2019.idx

# replace it, after the ZipNum is rebuilt
python -m pywb_arquivo.lmdb_zipnum_index load --drop --env /data/indexes_cdx/idx.lmdb --db RAQ2019 \
    /data/indexes_cdx/RAQ2019/RAQ2019.idx

# validate the .idx and show what would change, without writing
python -m pywb_arquivo.lmdb_zipnum_index load --dry-run --drop --env /data/indexes_cdx/idx.lmdb --db RAQ2019 \
    /data/indexes_cdx/RAQ2019/RAQ2019.idx

# number of entries of each named database
python -m pywb_arquivo.lmdb_zipnum_index stats --env /data/indexes_cdx/idx.lmdb
```

| option | |
|---|---|
| `--env` | LMDB environment directory |
| `--db` | named database, eg. the ZipNum name |
| `--dry-run` | validate the `.idx` and show the added, unchanged and dropped lines, without writing |
| `--drop` (`--recreate`) | replace the lines of a database that already has some |
| `--map-size` | max size of the environment in GiB (default: 64), only the used space takes disk space |

* A ZipNum is rebuilt as a whole, so a database is always loaded from a whole `.idx`: loading into a
  database with lines needs `--drop`.
* Each load is a single LMDB write transaction: pywb keeps reading the previous version until it is
  committed, and a failed load doesn't change the database (nor creates it). Repeated `--drop` loads
  grow `data.mdb` up to about 3 times the database size, then its free pages are reused; `mdb_copy -c`
  writes a compacted copy.
* The `.idx` is validated before it is committed, as pywb would return wrong results otherwise:
  * each line has the `urlkey timestamp`, part, offset, length and line number fields, separated by tabs;
  * the line number is the 1-based number of the line. `flat-cdxj-to-zipnum` writes it since
    [arquivo/replay-cdxj-indexing-tools#101](https://github.com/arquivo/replay-cdxj-indexing-tools/pull/101),
    older `.idx` files have 1 on every line and must be rebuilt;
  * the lines are sorted by their first field.
* The ZipNum shards and the `.idx` file must be the ones the database was loaded from: the database has
  the offsets of the blocks on the shards.

## Design

Each `.idx` line is an LMDB entry:

| | |
|---|---|
| key | the first field of the line (`urlkey timestamp`) cut to its first 500 bytes, a tab and the 8 byte big-endian line number |
| value | the rest of the line: the rest of the first field (over 500 bytes), and the part, offset, length and line number fields |

* LMDB keys have at most 511 bytes. The line is the key without the line number followed by the value,
  and is compared whole, like pywb compares the `.idx` lines.
* The line number keeps the order of the file, and makes unique the keys of consecutive blocks that
  start with the same `urlkey timestamp` (eg. a URL with thousands of captures on the same second).
* LMDB sorts the keys bytewise, like the `.idx` file (`LC_ALL=C`). The tab after the key prefix sorts
  like the tab after the first field of the line, so the keys are on the order of the lines, also for
  first fields over 500 bytes or with the same first 500 bytes.

pywb's `compute_page_range` finds the blocks of a query with `search(key, prev_size=1)` and
`iter_range(start, end, prev_size=1)`: the block of the first line `>= key`, and the one before, where
the matching lines can start. The LMDB version positions a cursor on the first key `>=` the query key
cut to 500 bytes (and before any tab, as the query keys have none), moves forward while the whole line
is smaller than the query key, then back `prev_size` lines. Without any line `>= key`, it returns the
last line, as the binary search does.

## Benchmark

[`pywb_arquivo/zipnum_benchmark.py`](../pywb_arquivo/zipnum_benchmark.py) runs the same queries with
the `.idx` file and with LMDB, on forked worker processes like the uWSGI workers:

```bash
python -m pywb_arquivo.zipnum_benchmark run --idx /data/indexes_cdx/RAQ2019/RAQ2019.idx \
    --lmdb 'lmdb:///data/indexes_cdx/idx.lmdb?db=RAQ2019' --cdxj /data/indexes_cdx/RAQ2019.cdxj \
    --workers 1,4,16 --json results.json

# the same, after dropping the .idx, LMDB and shards from the page cache
python -m pywb_arquivo.zipnum_benchmark run --cold ...

# only the .idx lookups, without the shards
python -m pywb_arquivo.zipnum_benchmark run --idx-only ...
```

* The urlkeys are sampled from the CDXJ files of the ZipNum (`--cdxj`), or from the `.idx`, plus 10% of
  missing ones. 80% of the queries are exact, like the replay ones, 10% prefix and 10% domain queries,
  of the first page with pywb's `max_blocks` (10 by default).
* Before the runs, it checks that both return the same `.idx` lines and CDX lines for every query of the
  sample.
* Each query is timed whole, and its `.idx` part (`compute_page_range`). It reports the latency
  percentiles, the throughput of all the workers, the CPU time, major page faults and block reads per
  query, and how much of the `.idx` (or `data.mdb`) and of the shards is on the page cache.
* Each worker does one query before the timed ones, which opens LMDB, as on a long-lived uWSGI worker.

`generate` writes a sorted synthetic `.idx` of the size of the production ZipNums, from the first fields
of CDXJ files, with fake shards, to time only the `.idx` (`--idx-only`):

```bash
python -m pywb_arquivo.zipnum_benchmark generate --lines 6500000 --block-size 3000 \
    --cdxj /data/indexes_cdx/RAQ2019.cdxj --cdxj /data/indexes_cdx/SAWP5.cdxj /data/bench/big-3000.idx
```

## Results

Run on a laptop (Intel i5-1345U, 12 threads, 30 GiB RAM, NVMe SSD), on AC power, with two sets of `.idx`
files, each with 3000, 1000 and 500 CDX lines per block. **They aren't the production ZipNums**: the
results must be confirmed with the real production `.idx` and, if possible, on the server.

* **RAQ2019**: ZipNums built by `flat-cdxj-to-zipnum` from the RAQ2019 CDXJ index (15.3 GB), with their
  shards (1.2 GB per block size).
* **Production-sized**: `.idx` files written by `generate` from the first fields of 4 CDXJ indexes
  (45 GB), with a number of lines of the order of the production ZipNums, without shards (`--idx-only`).
  Their lines are longer than RAQ2019's (about 330 against 150 bytes on average), 10% of them with a first
  field over 500 bytes.

| `.idx` | block size | lines | first fields over 500 bytes | repeated first fields | `.idx` file | LMDB database | load | load max RSS |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| RAQ2019 | 3000 | 9,820 | 173 | 323 | 1.4 MiB | 1.7 MiB (1.24×) | 0.5 s | 57 MB |
| RAQ2019 | 1000 | 29,459 | 509 | 1,124 | 4.2 MiB | 5.2 MiB (1.24×) | 0.4 s | 61 MB |
| RAQ2019 | 500 | 58,918 | 1,005 | 2,762 | 8.4 MiB | 10.4 MiB (1.24×) | 0.4 s | 67 MB |
| production-sized | 3000 | 5,579,896 | 568,807 | 24,302 | 1,778 MiB | 2,272 MiB (1.28×) | 9 s | 0.75 GB |
| production-sized | 1000 | 16,739,687 | 1,706,557 | 153,589 | 5,336 MiB | 6,817 MiB (1.28×) | 26 s | 0.77 GB |
| production-sized | 500 | 33,479,373 | 3,412,894 | 637,684 | 10,630 MiB | 13,578 MiB (1.28×) | 68 s | 0.82 GB |

* **LMDB returned the same `.idx` lines (and CDX lines) as the `.idx` file for every query of every
  sample**: 20,000 queries on each `.idx`-only run, 2,000 on each run with the shards.
* `.idx` only: 20,000 queries per worker. With the shards: 1,000 queries per worker. Each worker runs the
  same queries with the `.idx` file and with LMDB.
* Warm: the page cache has what the correctness check read. Cold: the `.idx` file, `data.mdb` and the
  shards are dropped from the page cache before each run.
* The `.idx` columns are of `compute_page_range`, the whole query with `--idx-only`. CPU is per query.
* The results vary between runs on the laptop: the first two runs were about twice as slow as the others,
  and were repeated; repeated runs with the shards changed the p50 by up to ±30%. The `.idx` file and LMDB
  of the same run are comparable. With 16 workers on 12 threads, the 3 ms p99 of the `.idx` file is the
  time slice of the scheduler.

### Block size 3000

`.idx` lookups only:

| `.idx` | page cache | workers | file p50 µs | LMDB p50 µs | file p99 µs | LMDB p99 µs | file queries/s | LMDB queries/s | file CPU µs | LMDB CPU µs | p50 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| RAQ2019 | warm | 1 | 41 | 10 | 106 | 16 | 16,464 | 39,623 | 60 | 25 | 3.9× faster |
| RAQ2019 | warm | 4 | 48 | 12 | 114 | 29 | 43,017 | 99,317 | 77 | 33 | 3.9× faster |
| RAQ2019 | warm | 16 | 95 | 25 | 303 | 38 | 83,401 | 194,000 | 124 | 54 | 3.8× faster |
| RAQ2019 | cold | 1 | 42 | 11 | 70 | 89 | 16,428 | 35,794 | 60 | 26 | 3.8× faster |
| RAQ2019 | cold | 4 | 57 | 15 | 151 | 40 | 35,268 | 79,419 | 92 | 42 | 3.9× faster |
| RAQ2019 | cold | 16 | 155 | 40 | 3162 | 64 | 55,153 | 132,220 | 204 | 84 | 3.9× faster |
| production-sized | warm | 1 | 89 | 15 | 290 | 56 | 8,572 | 30,312 | 116 | 32 | 6.0× faster |
| production-sized | warm | 4 | 107 | 17 | 453 | 76 | 21,321 | 79,902 | 160 | 41 | 6.3× faster |
| production-sized | warm | 16 | 215 | 42 | 3293 | 234 | 40,067 | 118,853 | 283 | 90 | 5.1× faster |
| production-sized | cold | 1 | 242 | 120 | 1233 | 1131 | 2,990 | 4,468 | 160 | 79 | 2.0× faster |
| production-sized | cold | 4 | 212 | 36 | 1222 | 855 | 11,941 | 29,167 | 253 | 72 | 5.9× faster |
| production-sized | cold | 16 | 371 | 56 | 4258 | 1690 | 21,648 | 78,324 | 482 | 118 | 6.6× faster |

Whole queries, RAQ2019 with its shards, `max_blocks` 10:

| page cache | workers | `.idx` | queries/s | p50 ms | p95 ms | p99 ms | exact p50 ms | exact p99 ms | `.idx` p50 µs | `.idx` share | CPU ms/query |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| warm | 1 | file | 23 | 4.16 | 249.4 | 273.3 | 3.71 | 219.0 | 92 | 0.2% | 44.2 |
| warm | 1 | LMDB | 23 | 4.09 | 247.8 | 274.7 | 3.66 | 216.7 | 43 | 0.1% | 44.0 |
| warm | 4 | file | 55 | 5.04 | 445.2 | 586.3 | 4.43 | 303.7 | 119 | 0.2% | 65.6 |
| warm | 4 | LMDB | 55 | 4.92 | 321.2 | 563.6 | 4.31 | 270.2 | 51 | 0.1% | 62.3 |
| warm | 16 | file | 85 | 11.07 | 1077.5 | 1469.4 | 10.78 | 934.2 | 262 | 0.2% | 135.2 |
| warm | 16 | LMDB | 84 | 10.95 | 1087.5 | 1509.0 | 10.64 | 948.4 | 102 | 0.1% | 135.2 |
| cold | 1 | file | 25 | 3.77 | 220.3 | 247.6 | 3.68 | 196.5 | 80 | 0.3% | 39.6 |
| cold | 1 | LMDB | 25 | 3.72 | 219.9 | 242.7 | 3.62 | 193.1 | 40 | 0.5% | 39.3 |
| cold | 4 | file | 53 | 5.19 | 370.8 | 574.7 | 4.91 | 280.2 | 128 | 0.2% | 64.7 |
| cold | 4 | LMDB | 58 | 5.20 | 417.2 | 562.2 | 4.99 | 324.1 | 63 | 0.2% | 65.9 |
| cold | 16 | file | 85 | 11.27 | 1076.0 | 1458.9 | 10.87 | 935.2 | 267 | 0.2% | 135.5 |
| cold | 16 | LMDB | 85 | 11.14 | 1061.7 | 1411.7 | 10.71 | 926.5 | 102 | 0.1% | 135.0 |

### Block size 1000

`.idx` lookups only:

| `.idx` | page cache | workers | file p50 µs | LMDB p50 µs | file p99 µs | LMDB p99 µs | file queries/s | LMDB queries/s | file CPU µs | LMDB CPU µs | p50 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| RAQ2019 | warm | 1 | 43 | 13 | 66 | 34 | 16,446 | 31,885 | 60 | 31 | 3.4× faster |
| RAQ2019 | warm | 4 | 62 | 15 | 169 | 39 | 32,250 | 75,844 | 106 | 42 | 4.0× faster |
| RAQ2019 | warm | 16 | 160 | 42 | 3161 | 95 | 52,293 | 114,037 | 209 | 86 | 3.8× faster |
| RAQ2019 | cold | 1 | 48 | 11 | 118 | 99 | 14,313 | 32,614 | 68 | 26 | 4.4× faster |
| RAQ2019 | cold | 4 | 58 | 21 | 149 | 91 | 34,529 | 65,944 | 96 | 56 | 2.7× faster |
| RAQ2019 | cold | 16 | 161 | 41 | 3186 | 114 | 49,148 | 118,757 | 210 | 89 | 3.9× faster |
| production-sized | warm | 1 | 94 | 16 | 343 | 120 | 7,785 | 25,457 | 128 | 39 | 5.8× faster |
| production-sized | warm | 4 | 127 | 23 | 621 | 161 | 16,315 | 53,582 | 197 | 61 | 5.5× faster |
| production-sized | warm | 16 | 360 | 58 | 3959 | 1192 | 22,586 | 81,228 | 469 | 129 | 6.2× faster |
| production-sized | cold | 1 | 395 | 179 | 1896 | 2238 | 1,927 | 2,943 | 246 | 111 | 2.2× faster |
| production-sized | cold | 4 | 321 | 41 | 1946 | 1351 | 7,846 | 20,509 | 380 | 91 | 7.9× faster |
| production-sized | cold | 16 | 407 | 61 | 4973 | 3079 | 18,422 | 57,893 | 523 | 142 | 6.6× faster |

Whole queries, RAQ2019 with its shards, `max_blocks` 10:

| page cache | workers | `.idx` | queries/s | p50 ms | p95 ms | p99 ms | exact p50 ms | exact p99 ms | `.idx` p50 µs | `.idx` share | CPU ms/query |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| warm | 1 | file | 69 | 2.99 | 69.7 | 83.0 | 1.55 | 66.2 | 69 | 0.5% | 14.5 |
| warm | 1 | LMDB | 69 | 2.98 | 70.4 | 90.3 | 1.53 | 65.1 | 30 | 0.2% | 14.6 |
| warm | 4 | file | 142 | 3.78 | 148.3 | 181.9 | 2.14 | 151.3 | 111 | 0.5% | 23.9 |
| warm | 4 | LMDB | 144 | 3.70 | 150.1 | 181.2 | 2.03 | 152.2 | 49 | 0.2% | 23.7 |
| warm | 16 | file | 229 | 9.02 | 361.1 | 500.1 | 5.83 | 359.1 | 249 | 0.5% | 50.3 |
| warm | 16 | LMDB | 229 | 8.92 | 361.7 | 507.9 | 5.69 | 375.0 | 98 | 0.2% | 50.2 |
| cold | 1 | file | 66 | 3.07 | 70.4 | 83.4 | 2.60 | 68.3 | 78 | 1.1% | 14.7 |
| cold | 1 | LMDB | 66 | 3.04 | 70.2 | 86.2 | 2.66 | 66.4 | 53 | 1.5% | 14.7 |
| cold | 4 | file | 141 | 4.04 | 150.8 | 181.3 | 2.66 | 154.7 | 119 | 0.6% | 24.2 |
| cold | 4 | LMDB | 143 | 4.07 | 153.4 | 182.7 | 2.70 | 156.5 | 57 | 0.5% | 24.5 |
| cold | 16 | file | 227 | 9.03 | 357.6 | 502.9 | 5.98 | 349.5 | 253 | 0.5% | 50.3 |
| cold | 16 | LMDB | 229 | 8.93 | 357.0 | 492.8 | 5.84 | 366.2 | 99 | 0.3% | 50.1 |

### Block size 500

`.idx` lookups only:

| `.idx` | page cache | workers | file p50 µs | LMDB p50 µs | file p99 µs | LMDB p99 µs | file queries/s | LMDB queries/s | file CPU µs | LMDB CPU µs | p50 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| RAQ2019 | warm | 1 | 54 | 13 | 133 | 33 | 12,915 | 31,858 | 77 | 31 | 4.2× faster |
| RAQ2019 | warm | 4 | 66 | 17 | 177 | 44 | 28,279 | 70,784 | 115 | 46 | 3.9× faster |
| RAQ2019 | warm | 16 | 184 | 42 | 3233 | 121 | 44,065 | 108,934 | 231 | 90 | 4.4× faster |
| RAQ2019 | cold | 1 | 48 | 11 | 169 | 167 | 14,179 | 26,945 | 67 | 29 | 4.2× faster |
| RAQ2019 | cold | 4 | 62 | 17 | 160 | 117 | 32,000 | 68,548 | 103 | 48 | 3.6× faster |
| RAQ2019 | cold | 16 | 182 | 42 | 3215 | 166 | 48,391 | 117,683 | 228 | 89 | 4.3× faster |
| production-sized | warm | 1 | 95 | 17 | 353 | 215 | 7,724 | 21,806 | 129 | 45 | 5.6× faster |
| production-sized | warm | 4 | 144 | 25 | 684 | 295 | 15,836 | 45,974 | 220 | 74 | 5.7× faster |
| production-sized | warm | 16 | 388 | 61 | 4243 | 2289 | 21,441 | 68,917 | 505 | 151 | 6.3× faster |
| production-sized | cold | 1 | 440 | 185 | 1915 | 3481 | 1,907 | 2,478 | 196 | 98 | 2.4× faster |
| production-sized | cold | 4 | 185 | 35 | 1801 | 1722 | 10,875 | 17,064 | 223 | 88 | 5.3× faster |
| production-sized | cold | 16 | 409 | 63 | 4367 | 3107 | 20,171 | 50,990 | 525 | 156 | 6.5× faster |

Whole queries, RAQ2019 with its shards, `max_blocks` 10:

| page cache | workers | `.idx` | queries/s | p50 ms | p95 ms | p99 ms | exact p50 ms | exact p99 ms | `.idx` p50 µs | `.idx` share | CPU ms/query |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| warm | 1 | file | 135 | 0.53 | 33.2 | 52.4 | 0.48 | 31.2 | 69 | 1.1% | 7.4 |
| warm | 1 | LMDB | 135 | 0.50 | 33.2 | 52.3 | 0.45 | 31.6 | 25 | 0.4% | 7.4 |
| warm | 4 | file | 276 | 0.90 | 73.7 | 86.6 | 0.77 | 75.9 | 101 | 1.0% | 12.1 |
| warm | 4 | LMDB | 282 | 0.79 | 70.4 | 86.4 | 0.68 | 75.9 | 39 | 0.4% | 11.9 |
| warm | 16 | file | 440 | 1.82 | 190.4 | 249.4 | 1.50 | 207.5 | 251 | 1.0% | 26.2 |
| warm | 16 | LMDB | 443 | 1.65 | 190.3 | 256.5 | 1.35 | 208.0 | 86 | 0.3% | 26.1 |
| cold | 1 | file | 126 | 1.26 | 33.8 | 53.0 | 1.03 | 32.5 | 85 | 2.9% | 7.6 |
| cold | 1 | LMDB | 127 | 1.18 | 33.6 | 52.9 | 0.97 | 32.9 | 58 | 3.1% | 7.5 |
| cold | 4 | file | 271 | 1.10 | 78.6 | 91.1 | 1.00 | 80.5 | 122 | 1.2% | 12.9 |
| cold | 4 | LMDB | 273 | 1.04 | 73.7 | 88.7 | 0.91 | 78.3 | 52 | 0.9% | 12.4 |
| cold | 16 | file | 426 | 2.34 | 190.8 | 255.7 | 1.64 | 203.5 | 257 | 1.0% | 26.4 |
| cold | 16 | LMDB | 428 | 1.81 | 186.5 | 254.2 | 1.43 | 211.8 | 90 | 0.5% | 26.3 |

### Block sizes with the same lines per page

pywb reads at most `max_blocks` blocks (10 by default) on the first page of a query. With the same
`max_blocks`, smaller blocks also mean fewer CDX lines on the first page of the queries with more than
`max_blocks` blocks: 2.2%, 4.2% and 4.7% of the exact queries of the sample at 3000, 1000 and 500 lines
per block, about 30% of the prefix queries and 95 to 98% of the domain queries. So the whole queries above
aren't comparable between block sizes. These runs compare them with the same 30,000 lines per page
(RAQ2019, warm, `.idx` file):

| block size | `max_blocks` | lines per page | workers | queries/s | p50 ms | p99 ms | exact p50 ms | exact p99 ms | CPU ms/query | CDX lines/query |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 3000 | 10 | 30,000 | 1 | 23 | 4.16 | 273.3 | 3.71 | 219.0 | 44.2 | 4,827 |
| 3000 | 10 | 30,000 | 4 | 55 | 5.04 | 586.3 | 4.43 | 303.7 | 65.6 | 4,729 |
| 3000 | 10 | 30,000 | 16 | 85 | 11.07 | 1469.4 | 10.78 | 934.2 | 135.2 | 4,760 |
| 1000 | 30 | 30,000 | 1 | 23 | 3.34 | 268.6 | 2.47 | 230.2 | 44.1 | 5,003 |
| 1000 | 30 | 30,000 | 4 | 46 | 4.15 | 654.8 | 2.61 | 331.0 | 70.8 | 4,890 |
| 1000 | 30 | 30,000 | 16 | 69 | 9.54 | 1945.1 | 7.26 | 1171.8 | 144.4 | 4,921 |
| 500 | 60 | 30,000 | 1 | 23 | 0.60 | 278.2 | 0.56 | 232.7 | 43.7 | 5,042 |
| 500 | 60 | 30,000 | 4 | 48 | 1.05 | 675.9 | 0.88 | 346.4 | 72.2 | 4,928 |
| 500 | 60 | 30,000 | 16 | 72 | 2.73 | 1933.0 | 1.81 | 1151.6 | 144.1 | 4,959 |
| 1000 | 10 | 10,000 | 1 | 69 | 2.99 | 83.0 | 1.55 | 66.2 | 14.5 | 1,806 |
| 1000 | 10 | 10,000 | 4 | 142 | 3.78 | 181.9 | 2.14 | 151.3 | 23.9 | 1,791 |
| 1000 | 10 | 10,000 | 16 | 229 | 9.02 | 500.1 | 5.83 | 359.1 | 50.3 | 1,808 |
| 500 | 10 | 5,000 | 1 | 135 | 0.53 | 52.4 | 0.48 | 31.2 | 7.4 | 973 |
| 500 | 10 | 5,000 | 4 | 276 | 0.90 | 86.6 | 0.77 | 75.9 | 12.1 | 970 |
| 500 | 10 | 5,000 | 16 | 440 | 1.82 | 249.4 | 1.50 | 207.5 | 26.2 | 983 |

The exact p50 at 1000 lines per block varied between 1.5 and 2.7 ms on repeated runs.

### Conclusions

* **`.idx` lookups**: LMDB is 2.7 to 4.4 times faster than the `.idx` file (p50) on the RAQ2019 `.idx`
  (1.4 to 8.4 MiB), and 5.1 to 7.9 times on the production-sized ones (1.8 to 10.6 GiB), with 2 to 4 times
  less CPU. With 16 workers, warm, its p99 is 38 to 121 µs against 0.3 to 3.2 ms on RAQ2019, and 0.2 to
  2.3 ms against 3.3 to 4.2 ms on the production-sized `.idx`.
* The exception is a single worker on a cold production-sized `.idx`: LMDB is only 2.0 to 2.4 times faster
  at the p50, and its p99 is similar or higher (1.1 to 3.5 ms against 1.2 to 1.9 ms), probably because each
  cursor lookup reads several 4 KiB pages of the B+tree from the disk.
* LMDB lookups barely grow with the `.idx`: from the RAQ2019 `.idx` of 500 lines per block to the
  production-sized one (about 1,300 times bigger), the warm p50 with 1 worker goes from 13 to 17 µs with
  LMDB, and from 54 to 95 µs with the file.
* **Whole queries**: the `.idx` is 0.1 to 3% of the time of a query on the RAQ2019 ZipNums. Reading,
  decompressing and parsing the blocks of the shards takes the rest, 7 to 135 ms of CPU per query on
  average. LMDB makes no measurable difference on the whole queries, below the variation between runs.
* **The block size matters much more than the `.idx`**. With the same lines per page, 500 lines per block
  make the exact queries 5 to 7 times faster at the p50 than 3000 (0.56 against 3.71 ms with 1 worker,
  1.81 against 10.78 ms with 16), as pywb decompresses and parses 500 lines instead of 3000 to find a URL.
  The queries that read whole pages take as long or longer (the same CPU per query, p99 1.9 against 1.5 s
  and 15% less throughput with 16 workers), as they read 60 blocks instead of 10.
* Smaller blocks make the `.idx` 6 times bigger, and its lookups a bigger part of the queries: on the
  production-sized `.idx` of 500 lines per block, the `.idx` file takes 95 to 388 µs (warm p50, 1 to 16
  workers), about 15 to 20% of an exact query of 0.56 to 1.81 ms on RAQ2019. LMDB takes 17 to 61 µs.

### Recommendation

* **Don't enable the LMDB `.idx` alone with blocks of 3000 lines**: it saves 0.05 to 0.16 ms of queries
  of 4 to 11 ms (p50), less than the variation between runs, and adds a step to every ZipNum update.
* **Reduce the block size to 500 lines**, with `max_blocks` 60 to keep the 30,000 lines per page (a
  separate change, out of the scope of this PoC). It is the bigger gain: most replay queries are exact,
  and they are 5 to 7 times faster at the p50.
* **Then enable the LMDB `.idx`**: with the 6 times bigger `.idx`, LMDB makes its lookups 5 to 6 times
  faster and its p99 lower with many workers. It costs a `data.mdb` 1.28 times the size of the `.idx`, a
  load of about a minute per 10 GiB of `.idx`, and a reload whenever the ZipNum is rebuilt, as the
  database has the offsets of the blocks on the shards.
* Confirm both with the real production `.idx`, and on the server with its number of uWSGI workers,
  before enabling them.
