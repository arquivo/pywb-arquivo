import gzip
import os

from pywb.utils.canonicalize import canonicalize


def cdxj_line(url, timestamp, **fields):
    json_fields = ', '.join('"{0}": "{1}"'.format(name, value) for name, value in dict(url=url, **fields).items())
    return '{0} {1} {{{2}}}\n'.format(canonicalize(url), timestamp, json_fields).encode('utf-8')


def build_zipnum(directory, lines, lines_per_block, base='test', shards=2):
    """Write a ZipNum of the sorted CDXJ ``lines``, like ``flat-cdxj-to-zipnum``:
    ``<base>-NN.cdx.gz`` shards of gzip blocks, the ``<base>.idx`` with the
    1-based line numbers and the ``<base>.loc``. Return the ``.idx`` path."""
    os.makedirs(directory, exist_ok=True)
    blocks = [lines[i:i + lines_per_block] for i in range(0, len(lines), lines_per_block)]
    blocks_per_shard = -(-len(blocks) // shards)
    idx_lines = []
    loc_lines = []
    for shard in range(shards):
        part = '{0}-{1:02d}.cdx.gz'.format(base, shard + 1)
        loc_lines.append('{0}\t{0}\n'.format(part))
        with open(os.path.join(directory, part), 'wb') as out:
            for block in blocks[shard * blocks_per_shard:(shard + 1) * blocks_per_shard]:
                data = gzip.compress(b''.join(block), mtime=0)
                first_field = block[0].partition(b' {')[0]
                idx_lines.append(b'%s\t%s\t%d\t%d\t%d\n' % (first_field, part.encode('ascii'), out.tell(),
                                                             len(data), len(idx_lines) + 1))
                out.write(data)

    idx = os.path.join(directory, base + '.idx')
    with open(idx, 'wb') as out:
        out.writelines(idx_lines)
    with open(os.path.join(directory, base + '.loc'), 'w') as out:
        out.writelines(loc_lines)
    return idx
