import tempfile
import unittest
from pathlib import Path

from buildchecker.fullcheck import trace_events, Unsupported


class TestResumedSyscallWithoutStartA12(unittest.TestCase):
    """A12 E5-E7 扩展测试（选项 A）：无起点 resumed 系统调用必须显式拒绝"""

    def test_resumed_syscall_without_start_fails_explicitly(self):
        d = Path(tempfile.mkdtemp())
        p = d / "t.10"
        p.write_text("<... openat resumed>) = 3\n")
        # 部分实现要求传目录，部分实现要求传文件，做兼容处理
        try:
            with self.assertRaisesRegex(Unsupported, "Resumed syscall without start"):
                trace_events(d)
            return
        except AssertionError:
            raise
        except Exception:
            pass

        with self.assertRaisesRegex(Unsupported, "Resumed syscall without start"):
            trace_events(str(p))


if __name__ == "__main__":
    unittest.main()
