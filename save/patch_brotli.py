import pathlib
import warcio

warcio_path = pathlib.Path(warcio.__file__).parent / 'bufferedreaders.py'
content = warcio_path.read_text()

# Add new init functions before the class definition
insert_marker = '#=================================================================\nclass BufferedReader(object):'
new_functions = '''def try_brotli_init():
    try:
        import brotli

        class BrotliDecompressor:
            def __init__(self):
                self._decomp = brotli.Decompressor()
                self.unused_data = None
            def decompress(self, data):
                return self._decomp.process(data)

        BufferedReader.DECOMPRESSORS['br'] = BrotliDecompressor
    except ImportError:  #pragma: no cover
        pass


def try_zstd_init():
    try:
        import zstandard

        class ZstdDecompressor:
            def __init__(self):
                self._ctx = zstandard.ZstdDecompressor()
                self.unused_data = None
            def decompress(self, data):
                return self._ctx.decompress(data)

        BufferedReader.DECOMPRESSORS['zstd'] = ZstdDecompressor
    except ImportError:  #pragma: no cover
        pass


#=================================================================
class BufferedReader(object):'''

if insert_marker in content:
    content = content.replace(insert_marker, new_functions)

# Ensure init calls are at the end
if content.strip().endswith('try_brotli_init()'):
    content = content.rstrip() + '\ntry_zstd_init()\n'
elif 'try_zstd_init()' not in content:
    # If try_brotli_init() is there but not try_zstd_init(), add it
    content = content.replace('try_brotli_init()', 'try_brotli_init()\ntry_zstd_init()')

warcio_path.write_text(content)
print('Patch applied successfully!')

