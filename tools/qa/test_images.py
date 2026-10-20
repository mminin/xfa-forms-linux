#!/usr/bin/env python3
"""Compare decoded samples with Pillow, then mutate each synthetic seed.

IMAGE_PROBE=/path/to/image-probe python3 tools/qa/test_images.py
Requires Pillow. XFA_QA_MUTATIONS sets deterministic mutations per seed.
"""
from pathlib import Path
import os
import resource
import struct
import subprocess
import tempfile
import unittest

from PIL import Image


class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = str(Path(os.environ['IMAGE_PROBE']).resolve())
        cls.temp = tempfile.TemporaryDirectory(prefix='xfa-images-')
        cls.out = Path(os.environ.get('XFA_QA_OUTPUT', cls.temp.name)).resolve()
        cls.out.mkdir(parents=True, exist_ok=True)
        cls.seeds = []
        rgba = Image.new('RGBA', (7, 5))
        rgba.putdata([(x * 31, y * 47, (x + y) * 19, (x * 37 + y * 13) % 256)
                      for y in range(5) for x in range(7)])
        for mode in ['RGB', 'RGBA', 'L', 'LA', '1', 'P']:
            image = rgba.convert(mode)
            for fmt, options in [('PNG', {}), ('TIFF', {}), ('TIFF', {'compression': 'tiff_lzw'}),
                                 ('TIFF', {'compression': 'tiff_adobe_deflate'}), ('TIFF', {'compression': 'packbits'}),
                                 ('BMP', {}), ('GIF', {})]:
                if mode == 'LA' and fmt in ['BMP', 'GIF']:
                    continue
                path = cls.out / f'{mode}-{fmt}-{options.get("compression", "raw")}.{fmt.lower()}'
                image.save(path, fmt, **options)
                cls.seeds.append(path)
        for mode in ['L', 'RGB', 'CMYK']:
            path = cls.out / f'{mode}.jpg'
            rgba.convert(mode).save(path, 'JPEG')
            cls.seeds.append(path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_reference_pixels(self):
        for path in self.seeds:
            with self.subTest(image=path.name):
                run = subprocess.run([self.probe, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace')[-1800:])
                header, raw = run.stdout.split(b'\n', 1)
                kind, w, h = header.split()
                with Image.open(path) as reference:
                    self.assertEqual((int(w), int(h)), reference.size)
                    if kind == b'JPEG':
                        continue
                    expected = reference.convert('RGBA').tobytes()
                self.assertEqual(len(raw), len(expected))
                for i in range(0, len(raw), 4):
                    self.assertEqual(raw[i + 3], expected[i + 3], f'alpha at pixel {i // 4}')
                    if expected[i + 3]:
                        self.assertEqual(raw[i:i + 3], expected[i:i + 3], f'color at pixel {i // 4}')

    def test_truncated_large_images(self):
        # A few bytes must not claim tens of megapixels of padding.
        tiff = self.out / 'P-TIFF-raw.tiff'
        data = bytearray(tiff.read_bytes())
        ifd = int.from_bytes(data[4:8], 'little')
        for k in range(int.from_bytes(data[ifd:ifd + 2], 'little')):
            e = ifd + 2 + 12 * k
            if int.from_bytes(data[e:e + 2], 'little') == 256:
                data[e + 8:e + 12] = (13000711).to_bytes(4, 'little')
        gif = (b'GIF89a' + struct.pack('<HHBBB', 8192, 8191, 0x80, 0, 0) + b'\0\0\0\xff\xff\xff'
               + b',' + struct.pack('<HHHHB', 0, 0, 8192, 8191, 0) + b'\x02\x02\x44\x01\x00;')
        for name, content in [('wide.tiff', bytes(data)), ('wide.gif', gif)]:
            with self.subTest(image=name):
                path = self.out / name
                path.write_bytes(content)
                run = subprocess.run([self.probe, str(path)], stdout=subprocess.DEVNULL, timeout=2)
                self.assertEqual(run.returncode, 1)

    def test_mutations(self):
        count = os.environ.get('XFA_QA_MUTATIONS', '500')
        for path in self.seeds:
            with self.subTest(image=path.name):
                log = self.out / (path.name + '.log')
                with log.open('wb') as stream:
                    run = subprocess.run([self.probe, str(path), count], stdout=stream, stderr=stream, timeout=60)
                self.assertEqual(run.returncode, 0, log.read_text(errors='replace')[-2000:])


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    unittest.main(verbosity=2)
