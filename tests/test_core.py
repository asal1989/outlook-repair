"""Unit tests for core modules."""

import os
import struct
import tempfile
import unittest

from outlook_repair.core.backup import create_backup, verify_backup
from outlook_repair.core.scanner import _fmt_size, scan_directory
from outlook_repair.core.validator import validate_file


class TestFmtSize(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(_fmt_size(512), '512.0 B')

    def test_kilobytes(self):
        self.assertIn('KB', _fmt_size(2048))

    def test_megabytes(self):
        self.assertIn('MB', _fmt_size(5 * 1024 * 1024))


class TestScanner(unittest.TestCase):
    def test_scan_finds_pst(self):
        with tempfile.TemporaryDirectory() as d:
            pst = os.path.join(d, 'test.pst')
            with open(pst, 'wb') as f:
                f.write(b'\x21\x42\x44\x4E' + b'\x00' * 560)
            found = scan_directory(d)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]['name'], 'test.pst')
            self.assertEqual(found[0]['extension'], '.pst')

    def test_scan_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(scan_directory(d), [])

    def test_scan_nonexistent(self):
        self.assertEqual(scan_directory('/nonexistent/path/xyz'), [])


class TestValidator(unittest.TestCase):
    def _make_pst(self, tmpdir, version=23, bad_magic=False):
        path = os.path.join(tmpdir, 'test.pst')
        magic = b'\x00\x00\x00\x00' if bad_magic else b'\x21\x42\x44\x4E'
        header = magic + b'\x00' * 6 + struct.pack('<H', version) + b'\x00' * 552
        with open(path, 'wb') as f:
            f.write(header)
        return path

    def test_valid_pst(self):
        with tempfile.TemporaryDirectory() as d:
            r = validate_file(self._make_pst(d))
            self.assertTrue(r.is_valid)
            self.assertEqual(r.file_type, 'PST')
            self.assertIn('Unicode', r.version)

    def test_bad_magic(self):
        with tempfile.TemporaryDirectory() as d:
            r = validate_file(self._make_pst(d, bad_magic=True))
            self.assertFalse(r.is_valid)
            self.assertTrue(any('magic' in e.lower() for e in r.errors))

    def test_file_not_found(self):
        r = validate_file('/no/such/file.pst')
        self.assertFalse(r.is_valid)
        self.assertTrue(r.errors)

    def test_valid_lst(self):
        with tempfile.TemporaryDirectory() as d:
            lst = os.path.join(d, 'ac.lst')
            with open(lst, 'wb') as f:
                f.write(b'\x0D\xF0\xAD\xBA' + b'\x00' * 20)
            r = validate_file(lst)
            self.assertTrue(r.is_valid)
            self.assertIn('NK2', r.version)


class TestBackup(unittest.TestCase):
    def test_creates_bak(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'data.pst')
            with open(src, 'wb') as f:
                f.write(b'test content')
            bak = create_backup(src)
            self.assertTrue(os.path.isfile(bak))
            self.assertTrue(bak.endswith('.bak'))

    def test_verify_matches(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'data.pst')
            with open(src, 'wb') as f:
                f.write(b'hello world')
            bak = create_backup(src)
            self.assertTrue(verify_backup(src, bak))

    def test_source_not_found(self):
        with self.assertRaises(FileNotFoundError):
            create_backup('/no/such/file.pst')


if __name__ == '__main__':
    unittest.main()
