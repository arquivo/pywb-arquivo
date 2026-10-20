# LMDB path index (PoC)

Proof of concept of [arquivo/pwa-technologies#1672](https://github.com/arquivo/pwa-technologies/issues/1672):
resolve the WARC file name of each CDX line to the location of the WARC file with an
[LMDB](http://www.lmdb.tech/doc/) database, instead of the TSV path index of pywb's `PathIndexResolver`.

| | TSV path index | LMDB path index |
|---|---|---|
| resolver | `PathIndexResolver` (pywb) | [`LMDBPathIndexResolver`](../pywb_arquivo/lmdb_path_resolver.py) |
| lookup | open the file, binary search over 8 KiB blocks, parse the lines | B+tree point lookup on a memory map |
| `archive_paths` | `/data/warcIndex/branchA/AWP1.tsv` | `lmdb:///data/warcIndex/pathindex.lmdb?db=branchA` |

The LMDB database returns the same paths as the TSV path index for the same WARC file name, the
values are loaded from the TSV files.

## Branches

A single LMDB environment (a directory with `data.mdb` and `lock.mdb`) has one named database per
branch, eg. `branchA` and `branchB`, each one loaded from the TSV files of its branch. Each named
database is configured as an independent `archive_paths` entry of the pywb `config.yaml`:

```yaml
collections:
  wayback:
    index: ...
    archive_paths:
      - lmdb:///data/warcIndex/pathindex.lmdb?db=branchA
      - lmdb:///data/warcIndex/pathindex.lmdb?db=branchB
```

pywb tries each `archive_paths` resolver in order, the `branchB` database is only used when the WARC
file is missing on the `branchA` database, or when it can't be loaded from the `branchA` paths.
Use a single entry to use a single branch, or swap them to make `branchB` the primary one.

The databases are independent:

* loading (or recreating) one of them doesn't change the others;
* a missing environment or named database is logged, skipped, and opened again after 60 seconds,
  without affecting the other resolvers.

## Loading the TSV path indexes

[`pywb_arquivo/lmdb_path_index.py`](../pywb_arquivo/lmdb_path_index.py) loads TSV path index files
(and all the files of directories) into a named database, creating the environment if needed:

```bash
# load or update a collection on the branchA database
python -m pywb_arquivo.lmdb_path_index load --env /data/warcIndex/pathindex.lmdb --db branchA \
    /data/warcIndex/branchA/AWP1.tsv

# only show what would change: added, updated, unchanged and dropped entries
python -m pywb_arquivo.lmdb_path_index load --dry-run --env /data/warcIndex/pathindex.lmdb --db branchA \
    /data/warcIndex/branchA/AWP1.tsv

# recreate the branchA database from all the .tsv files of its directory
python -m pywb_arquivo.lmdb_path_index load --env /data/warcIndex/pathindex.lmdb --db branchA \
    --drop --pattern '.*\.tsv' /data/warcIndex/branchA/

# number of entries of each named database
python -m pywb_arquivo.lmdb_path_index stats --env /data/warcIndex/pathindex.lmdb
```

| option | |
|---|---|
| `--env` | LMDB environment directory |
| `--db` | named database, eg. `branchA` |
| `--dry-run` | show what would change without writing, it doesn't need write access |
| `--drop` (`--recreate`) | empty the named database before loading, to remove the WARC files that aren't on the TSV files anymore |
| `--pattern` | regex that the names of the files of the directories must fully match, eg. `'AWP.*\.tsv'` (default: all the files) |
| `--map-size` | max size of the environment in GiB (default: 64), only the used space takes disk space |

* Loading adds the new WARC files and replaces the paths of the existing ones, without removing the
  other WARC files of the database, so it can run once for each new or updated collection.
* Each run is a single LMDB write transaction: pywb keeps reading the previous version of the database
  until the load is committed, also with `--drop`. A failed load doesn't change the database.
  As LMDB keeps the previous versions until no one can read them, repeating `--drop` (or updating most
  of the WARC files) grows `data.mdb` up to about 3 times the size of the database, then the free
  space is reused. LMDB doesn't shrink the file, `mdb_copy -c` writes a compacted copy.
* Only one load can write to an environment at a time, the others wait for it.
* The lines are parsed like pywb's `PathIndexResolver`: the paths of consecutive lines of the same WARC
  file are joined, lines without paths are skipped. A WARC file on more than one file keeps the paths of
  the last one. The TSV files must be sorted, like for `PathIndexResolver`, the unsorted lines are counted.
* WARC file names longer than 511 bytes (the LMDB key size limit) are skipped.

## Running on pywb

The `lmdb://` resolver is added to pywb by the [`pywb_arquivo.wayback`](../pywb_arquivo/wayback.py)
WSGI application, used by the `framed` and `unframed` `uwsgi.ini` instead of `pywb.apps.wayback`.
docker compose mounts `WARC_INDEX_FOLDER` (default: `/data/warcIndex`) on `/data/warcIndex`.

* pywb opens the environment read only, but it needs write access to `lock.mdb`, where LMDB keeps
  track of its readers, so it reads a consistent version while the loader writes.
* The environment is opened on the first lookup of each uWSGI worker, as LMDB can't be used after
  `fork()` and it can only be opened once per process. All the resolvers of a worker share it.
* The data is read through the memory map, from the OS page cache, shared by all the workers and
  pywb instances of the server. Only the pages used by the lookups are read.

## Benchmark

[`pywb_arquivo/path_index_benchmark.py`](../pywb_arquivo/path_index_benchmark.py) compares the path
indexes, with the TSV files, an LMDB environment loaded from them and, optionally, the Redis hashes of
pywb's `RedisResolver`, loaded from them with `path-index-to-redis` (replay-cdxj-indexing-tools):

```bash
python -m pywb_arquivo.path_index_benchmark run \
    --tsv /data/warcIndex/branchA/AWP1.tsv --tsv /data/warcIndex/branchA/AWP2.tsv \
    --lmdb 'lmdb:///data/warcIndex/pathindex.lmdb?db=branchA' \
    --redis redis://localhost:6379/0/pathindex:branchA \
    --workers 1,4,16 --json results.json

# the same, after dropping the index files from the page cache
python -m pywb_arquivo.path_index_benchmark run --cold ...
```

It samples WARC file names from the TSV files (plus 10% missing ones), checks that the others return the
same paths as the TSV files (only the first one for Redis, which keeps a single path per WARC file), and
resolves them on forked worker processes, as pywb does: the first path of the first resolver with paths.
It reports the latency percentiles, the throughput of all the workers, the CPU time, major page faults
and block reads per lookup, and how much of the index files is on the page cache. For Redis, it also
reports the CPU time of the Redis server per lookup, and its memory.

`generate` writes a sorted synthetic TSV path index, to try it without the real ones:

```bash
python -m pywb_arquivo.path_index_benchmark generate --size 1 /tmp/bench/AWP.tsv
```

### Results with a real path index

Run on a laptop (Intel i5-1345U, 12 threads, 30 GiB RAM, NVMe SSD) with the arclists of the 202
collections of one branch, converted to a path index like `arclist-to-path-index` (`name<tab>url`,
sorted with `LC_ALL=C sort`): 2.3 GiB, 14.6 M lines, 14.56 M WARC files (33 k of them on 2 or 3 lines).
The other branch is the same path index with a different server on each url, the same size.
The `archive_paths` order of pywb was used: `branchA` and then `branchB`, for both the TSV files and
the LMDB named databases of a single environment.

Redis 7.2 ran on the same laptop, on localhost, in memory only (no persistence), with a hash per
branch (`pathindex:branchA` and `pathindex:branchB`) loaded with `path-index-to-redis`.

| | TSV | LMDB | Redis |
|---|--:|--:|--:|
| size of both branches | 4.5 GiB (2 files) | 5.2 GiB (1 `data.mdb`, 2 named databases) | 6.1 GiB of RAM, always resident |
| load of each branch | | 19 to 24 s, 0.6 GiB max RSS | 125 s (`path-index-to-redis`) |
| `--dry-run` of one collection (440 k WARC files) | | 1.5 s | |

* LMDB returned the same paths as the TSV files for all the 22000 sampled WARC file names, 2000 of them
  missing. Redis returned a different first path for 103 of them (0.5%), all WARC files on more than
  one line of the TSV files with different paths: `path-index-to-redis` stores only the first path of
  each line, so the last line wins, and pywb has no other path of that branch to try.

| page cache | workers | resolver | lookups/s | p50 µs | p95 µs | p99 µs | CPU µs/lookup | Redis server CPU µs/lookup | page cache MiB |
|---|--:|---|--:|--:|--:|--:|--:|--:|--:|
| warm | 1 | TSV | 5,174 | 171.9 | 362.2 | 414.0 | 192.5 | - | 4,636 |
| warm | 1 | LMDB | 200,772 | 3.6 | 9.1 | 14.8 | 4.4 | - | 5,303 |
| warm | 1 | Redis | 12,739 | 64.8 | 177.7 | 302.4 | 51.6 | 32.5 | - |
| warm | 4 | TSV | 11,612 | 204.5 | 489.0 | 905.5 | 284.0 | - | 4,636 |
| warm | 4 | LMDB | 393,296 | 5.3 | 12.9 | 21.8 | 6.6 | - | 5,303 |
| warm | 4 | Redis | 80,019 | 43.9 | 87.2 | 118.4 | 37.3 | 10.3 | - |
| warm | 16 | TSV | 11,960 | 797.5 | 4013.0 | 7339.6 | 760.6 | - | 4,636 |
| warm | 16 | LMDB | 682,544 | 9.5 | 20.4 | 30.9 | 11.5 | - | 5,303 |
| warm | 16 | Redis | 71,865 | 202.7 | 394.5 | 554.8 | 52.1 | 13.8 | - |
| cold | 1 | TSV | 1,302 | 549.2 | 2030.5 | 3494.6 | 589.5 | - | 2,497 |
| cold | 1 | LMDB | 8,751 | 99.3 | 291.9 | 471.7 | 46.7 | - | 85 |
| cold | 1 | Redis | 13,941 | 62.6 | 155.2 | 241.8 | 47.5 | 29.8 | - |
| cold | 4 | TSV | 6,056 | 425.2 | 1715.5 | 3059.7 | 576.6 | - | 2,886 |
| cold | 4 | LMDB | 80,059 | 11.8 | 209.2 | 355.7 | 22.9 | - | 122 |
| cold | 4 | Redis | 103,555 | 32.2 | 67.5 | 139.9 | 27.0 | 7.8 | - |
| cold | 16 | TSV | 11,213 | 804.5 | 4170.7 | 7124.0 | 816.3 | - | 2,910 |
| cold | 16 | LMDB | 465,859 | 10.3 | 135.8 | 381.0 | 14.7 | - | 125 |
| cold | 16 | Redis | 71,705 | 201.4 | 392.5 | 557.0 | 53.2 | 13.9 | - |

* Warm, an LMDB lookup takes 4 to 10 µs (p50), Redis 44 to 203 µs and the TSV files 172 to 798 µs:
  LMDB is 40 to 85 times faster than the TSV files and 8 to 21 times faster than Redis, which is 3 to 5
  times faster than the TSV files.
* CPU per lookup, with the Redis server's: LMDB 4 to 12 µs, Redis 48 to 84 µs, TSV 190 to 760 µs.
* With 16 workers, LMDB does 680 k lookups/s, Redis 72 k and the TSV files 12 k. Redis stops growing
  after 4 workers: its single thread uses a whole core (14 µs × 72 k lookups/s), and every lookup is a
  round trip to it, here on localhost; on another server, each lookup also pays the network latency.
  The TSV throughput also stops growing after 4 workers.
* With 16 workers the p99 is 31 µs warm and 0.4 ms cold with LMDB, 0.55 ms with Redis, and 7.3 ms warm
  and 7.1 ms cold with the TSV files.
* Cold doesn't change Redis, which keeps everything in memory. LMDB reads its pages on the first lookups:
  with a single worker it is slower than Redis (p50 99 µs against 63 µs), with 4 workers its p99 is
  higher (356 µs against 140 µs), with 16 workers it is faster again. The 20000 lookups bring 0.1 GiB
  of LMDB to the page cache, and 2.5 to 2.9 GiB of the TSV files.
* Redis keeps both branches in memory all the time (6.1 GiB), LMDB only the pages used, which the
  kernel can reclaim. The warm `page cache MiB` includes what the loading and the sampling read.
* The `branchB` TSV file, database and hash are only read for the missing WARC files, as on pywb.

#### Conclusions

Compared with the TSV files, the change of each one (warm: the index files already on the page cache;
cold: dropped from it before the run; the Redis CPU includes the Redis server's):

| page cache | workers | resolver | p50 | p99 | lookups/s | CPU/lookup |
|---|--:|---|--:|--:|--:|--:|
| warm | 1 | Redis | −62% | −27% | +146% | −56% |
| warm | 1 | LMDB | −98% | −96% | +3,780% | −98% |
| warm | 4 | Redis | −79% | −87% | +589% | −83% |
| warm | 4 | LMDB | −97% | −98% | +3,287% | −98% |
| warm | 16 | Redis | −75% | −92% | +501% | −91% |
| warm | 16 | LMDB | −99% | −99.6% | +5,607% | −98.5% |
| cold | 1 | Redis | −89% | −93% | +971% | −87% |
| cold | 1 | LMDB | −82% | −87% | +572% | −92% |
| cold | 4 | Redis | −92% | −95% | +1,610% | −94% |
| cold | 4 | LMDB | −97% | −88% | +1,222% | −96% |
| cold | 16 | Redis | −75% | −92% | +539% | −92% |
| cold | 16 | LMDB | −99% | −95% | +4,054% | −98% |

LMDB compared with Redis:

| page cache | workers | p50 | p95 | p99 | lookups/s | CPU/lookup |
|---|--:|--:|--:|--:|--:|--:|
| warm | 1 | 18 × faster (−94%) | −95% | −95% | 16 × (+1,476%) | 19 × less (−95%) |
| warm | 4 | 8 × faster (−88%) | −85% | −82% | 5 × (+392%) | 7 × less (−86%) |
| warm | 16 | 21 × faster (−95%) | −95% | −94% | 9.5 × (+850%) | 6 × less (−83%) |
| cold | 1 | 1.6 × slower (+59%) | +88% | +95% | −37% | −40% |
| cold | 4 | 2.7 × faster (−63%) | +210% | +154% | −23% | −34% |
| cold | 16 | 20 × faster (−95%) | −65% | −32% | 6.5 × (+550%) | −78% |

| | TSV | Redis | LMDB |
|---|---|---|---|
| size of both branches | 4.5 GiB of files | 6.1 GiB (+35%), always in memory | 5.2 GiB (+15%), only the pages used on the page cache |
| load of each branch | | 125 s | 19 to 24 s (6 times faster than Redis) |
| same first path as the TSV files | | 99.5% | 100% |
| scaling | stops after 4 workers (12 k lookups/s) | stops after 4 workers, single server thread (72 k lookups/s) | 683 k lookups/s with 16 workers |
| service | none, files on the server | a separate service, a round trip per lookup | none, a file on the server |

* LMDB is the fastest path index. With the index on the page cache, the usual state of a busy server,
  it takes 96 to 99.6% less time and CPU per lookup than the TSV files, and 82 to 95% less than Redis:
  5 to 21 times faster than Redis, with 5 to 16 times its throughput and 6 to 19 times less CPU.
* Redis is 3 to 5 times faster than the TSV files, but keeps both branches in memory all the time,
  saturates its single thread after 4 workers, and loses the other paths of the WARC files on more than
  one line of the TSV files.
* Redis is only better right after the page cache is dropped, with 1 worker and, on the p95 and p99,
  with 4 workers: it keeps everything in memory, while LMDB reads its pages from disk on the first
  lookups. With 16 workers, LMDB is faster even then.
* Redis ran on the same laptop: a Redis on another server adds the network latency to each lookup, so
  the difference would be bigger.
* These results are from a laptop, with one real branch and a simulated second one; they still have to be
  confirmed on the server, with the real path indexes of both branches and the real number of workers.

### Results with synthetic path indexes

Run on a laptop (Intel i5-1345U, 12 threads, 30 GiB RAM, NVMe SSD), with synthetic sorted TSV path
indexes of 1, 4 and 8 GiB (about 170 bytes per line) generated by `generate`, one TSV file and one LMDB
named database each, 20000 sampled WARC file names plus 10% missing ones, 20000 lookups per worker.
**They aren't the real path indexes**, the benchmark must be repeated on the server with them.

| TSV | lines | LMDB `data.mdb` | load time | loader max RSS |
|--:|--:|--:|--:|--:|
| 1 GiB | 6.1 M | 1.2 GiB | 8 s | 0.6 GiB |
| 4 GiB | 24.3 M | 4.8 GiB | 35 s | 0.6 GiB |
| 8 GiB | 48.5 M | 9.4 GiB | 64 s | 0.6 GiB |

* Both returned the same paths for all the sampled WARC file names.
* On the 1 and 4 GiB tests, with the index on the page cache (warm), an LMDB lookup takes 2 to 3 µs
  (p50) against 140 to 180 µs with the TSV file, about 60 times faster, using 40 to 55 times less CPU.
* With 16 workers, the TSV p99 grows to 6.5 to 7.5 ms, LMDB stays under 0.5 ms on all the tests.
* From an empty page cache (cold), the TSV binary search, with the kernel readahead, brings most of the
  TSV file to the page cache after the 20000 lookups (1 to 4 GiB), LMDB only 0.1 GiB.
* On the 8 GiB test the TSV and LMDB files (17.6 GiB) didn't fit on the free page cache, so the warm
  test also read from the disk.
* The LMDB database is about 18% bigger than the TSV file.
* The warm `page cache MiB` also has what the loader and the previous runs left on the page cache, the
  cold one shows what the lookups need.

#### 1 GiB TSV (1024 MiB TSV, 1205 MiB LMDB, same results: 22000/22000)

| page cache | workers | resolver | lookups/s | p50 µs | p95 µs | p99 µs | CPU µs/lookup | page cache MiB |
|---|--:|---|--:|--:|--:|--:|--:|--:|
| warm | 1 | TSV | 7,047 | 139.9 | 159.1 | 171.8 | 141.7 | 1,024 |
| warm | 1 | LMDB | 280,484 | 2.2 | 5.3 | 8.5 | 3.2 | 1,205 |
| warm | 4 | TSV | 10,877 | 258.0 | 591.1 | 675.2 | 306.9 | 1,024 |
| warm | 4 | LMDB | 501,433 | 4.6 | 12.4 | 14.8 | 5.9 | 1,205 |
| warm | 16 | TSV | 15,179 | 518.4 | 3517.5 | 7492.8 | 601.5 | 1,024 |
| warm | 16 | LMDB | 1,009,568 | 6.8 | 12.8 | 16.2 | 7.8 | 1,205 |
| cold | 1 | TSV | 3,104 | 198.7 | 923.9 | 1865.9 | 276.8 | 998 |
| cold | 1 | LMDB | 11,276 | 74.5 | 231.3 | 351.5 | 36.0 | 66 |
| cold | 4 | TSV | 9,583 | 252.3 | 730.7 | 1223.2 | 328.9 | 1,019 |
| cold | 4 | LMDB | 106,743 | 7.7 | 170.3 | 251.4 | 16.1 | 94 |
| cold | 16 | TSV | 12,710 | 754.0 | 4028.6 | 6856.4 | 740.3 | 1,020 |
| cold | 16 | LMDB | 541,901 | 7.9 | 117.5 | 338.5 | 11.5 | 96 |

#### 4 GiB TSV (4096 MiB TSV, 4821 MiB LMDB, same results: 22000/22000)

| page cache | workers | resolver | lookups/s | p50 µs | p95 µs | p99 µs | CPU µs/lookup | page cache MiB |
|---|--:|---|--:|--:|--:|--:|--:|--:|
| warm | 1 | TSV | 5,423 | 182.4 | 215.7 | 241.3 | 184.0 | 3,909 |
| warm | 1 | LMDB | 259,078 | 3.1 | 5.2 | 6.6 | 3.4 | 1,763 |
| warm | 4 | TSV | 14,602 | 191.3 | 375.3 | 422.9 | 228.0 | 3,909 |
| warm | 4 | LMDB | 613,462 | 3.7 | 10.2 | 12.9 | 4.8 | 1,763 |
| warm | 16 | TSV | 14,059 | 611.4 | 3588.9 | 6557.0 | 701.9 | 3,890 |
| warm | 16 | LMDB | 881,528 | 7.9 | 15.4 | 21.6 | 9.5 | 1,663 |
| cold | 1 | TSV | 1,706 | 399.6 | 1562.0 | 2593.8 | 427.2 | 2,886 |
| cold | 1 | LMDB | 9,098 | 104.5 | 261.0 | 467.4 | 33.0 | 86 |
| cold | 4 | TSV | 9,063 | 300.5 | 1158.2 | 1813.1 | 364.6 | 3,376 |
| cold | 4 | LMDB | 73,217 | 10.6 | 230.9 | 379.4 | 21.6 | 126 |
| cold | 16 | TSV | 13,233 | 669.1 | 4006.7 | 5621.7 | 778.5 | 3,402 |
| cold | 16 | LMDB | 556,152 | 6.8 | 151.5 | 366.9 | 12.6 | 128 |

#### 8 GiB TSV (8192 MiB TSV, 9642 MiB LMDB, same results: 22000/22000)

| page cache | workers | resolver | lookups/s | p50 µs | p95 µs | p99 µs | CPU µs/lookup | page cache MiB |
|---|--:|---|--:|--:|--:|--:|--:|--:|
| warm | 1 | TSV | 2,084 | 380.8 | 1042.0 | 1533.8 | 363.6 | 4,316 |
| warm | 1 | LMDB | 8,841 | 126.9 | 255.2 | 371.9 | 41.6 | 102 |
| warm | 4 | TSV | 5,647 | 559.6 | 1641.8 | 2504.0 | 525.1 | 4,096 |
| warm | 4 | LMDB | 95,345 | 8.7 | 164.4 | 236.7 | 13.9 | 148 |
| warm | 16 | TSV | 7,628 | 1653.0 | 4967.7 | 6955.6 | 1051.8 | 3,548 |
| warm | 16 | LMDB | 183,884 | 17.9 | 289.6 | 483.1 | 29.6 | 142 |
| cold | 1 | TSV | 1,417 | 559.5 | 1684.4 | 2500.6 | 484.5 | 3,826 |
| cold | 1 | LMDB | 9,181 | 127.0 | 235.0 | 354.9 | 39.6 | 93 |
| cold | 4 | TSV | 6,026 | 464.5 | 1596.0 | 2482.7 | 484.2 | 3,767 |
| cold | 4 | LMDB | 100,023 | 6.9 | 166.9 | 230.1 | 13.7 | 139 |
| cold | 16 | TSV | 9,293 | 1201.2 | 4649.9 | 6631.7 | 1035.4 | 3,813 |
| cold | 16 | LMDB | 239,264 | 12.2 | 259.8 | 347.4 | 25.0 | 142 |
