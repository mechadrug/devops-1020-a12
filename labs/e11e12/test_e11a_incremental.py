"""回归测试：E11-A 增量扫描的刷新/复用与新增缺失依赖。"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'labs/e8e10'), str(ROOT / 'labs/e11e12')]
from lab import commit, fixture, scan


class IncrementalScan(unittest.TestCase):
    def test_unchanged_tree_reuses_both_targets(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'proj'
            fixture(p)
            baseline = scan(p, None)
            again = scan(p, baseline)
            self.assertEqual(again['reused'], ['main.o', 'helper.o'])
            self.assertEqual(again['refreshed'], [])
            self.assertEqual(again['added'], [])
            self.assertEqual(again['resolved'], [])

    def test_new_header_directive_refreshes_every_target(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'proj'
            fixture(p)
            baseline = scan(p, None)
            (p / 'extra2.h').write_text('#define EXTRA2 0\n')
            main = p / 'main.c'
            main.write_text('#include "extra2.h"\n' + main.read_text())
            head = commit(p, 'C1 add second header dependency')
            inc = scan(p, baseline)
            # E8-E10 的缓存键覆盖全部预处理指令，任一源文件变化都会刷新全部目标。
            self.assertEqual(inc['refreshed'], ['main.o', 'helper.o'])
            self.assertEqual(inc['reused'], [])
            self.assertIn(['MISSING', 'main.o', 'extra2.h'], inc['added'])
            self.assertEqual(inc['commit'], head)


if __name__ == '__main__':
    unittest.main()
