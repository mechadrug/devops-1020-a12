"""Boundary tests use independent miniature syscall transcripts."""
import tempfile
import unittest
from pathlib import Path
from buildchecker.fullcheck import (
    Unsupported,
    analyze,
    declaration_graph,
    execution_graph,
    project_path,
    split_args,
    trace_events,
)


class TestFullCheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.root = "/course/project"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        path = self.folder / name
        path.write_text(text, encoding="utf-8")
        return path

    def traces(self, reader_extra="", driver_before="", driver_after="", writer_extra=""):
        self.write("t.10", 'execve("/usr/bin/make", ["make", "app"], []) = 0\nclone(child_stack=NULL, flags=SIGCHLD) = 11\n')
        self.write("t.11", 'execve("/usr/bin/cc", ["cc", "-c", "unit.c", "-o", "unit.o"], []) = 0\n'
                   + driver_before + 'clone(child_stack=NULL, flags=SIGCHLD) = 12\n'
                   + driver_after + 'clone(child_stack=NULL, flags=SIGCHLD) = 13\n')
        self.write("t.12", 'execve("/usr/bin/cc1", ["cc1", "unit.c"], []) = 0\n'
                   + 'openat(AT_FDCWD, "unit.c", O_RDONLY) = 3\n'
                   + 'openat(AT_FDCWD, "needed.h", O_RDONLY) = 4\n' + reader_extra)
        self.write("t.13", 'execve("/usr/bin/as", ["as", "-o", "unit.o"], []) = 0\n'
                   + 'openat(AT_FDCWD, "unit.o", O_RDWR|O_CREAT|O_TRUNC, 0666) = 3\n' + writer_extra)

    def test_read_and_write_in_sibling_processes_join_one_job(self):
        self.traces()
        targets, processes = execution_graph(self.folder, self.root)
        self.assertEqual(set(targets["unit.o"]["dependencies"]), {"unit.c", "needed.h"})
        self.assertEqual(targets["unit.o"]["processes"], [11, 12, 13])
        self.assertEqual(next(p for p in processes if p["pid"] == 12)["job_pid"], 11)

    def test_failed_open_and_outside_project_are_not_dependencies(self):
        self.traces(reader_extra='openat(AT_FDCWD, "absent.h", O_RDONLY) = -1 ENOENT (No such file)\n'
                    'openat(AT_FDCWD, "/usr/include/stdio.h", O_RDONLY) = 5\n'
                    'openat(AT_FDCWD, "/course/project-other/secret.h", O_RDONLY) = 6\n')
        targets, _ = execution_graph(self.folder, self.root)
        self.assertEqual(set(targets["unit.o"]["dependencies"]), {"unit.c", "needed.h"})

    def test_failed_make_exec_and_failed_clone_do_not_create_fake_make_tree(self):
        self.traces()
        text=(self.folder / "t.11").read_text()
        self.write("t.11", 'execve("/missing/make", ["make"], []) = -1 ENOENT (No such file)\n'
                   'clone3({}, 88) = -1 ENOSYS (Not implemented)\n' + text)
        targets, _ = execution_graph(self.folder, self.root)
        self.assertIn("unit.o", targets)

    def test_cwd_is_inherited_at_fork_not_after_later_chdir(self):
        self.traces(driver_before='chdir("src") = 0\n', driver_after='chdir("../build") = 0\n')
        targets, _ = execution_graph(self.folder, self.root)
        self.assertEqual(set(targets["build/unit.o"]["dependencies"]), {"src/unit.c", "src/needed.h"})

    def test_deleted_internal_output_does_not_become_dependency(self):
        self.traces(writer_extra='openat(AT_FDCWD, "temporary.s", O_WRONLY|O_CREAT, 0666) = 4\n'
                    'openat(AT_FDCWD, "temporary.s", O_RDONLY) = 5\n'
                    'unlink("temporary.s") = 0\n')
        targets, _ = execution_graph(self.folder, self.root)
        self.assertEqual(set(targets), {"unit.o"})
        self.assertNotIn("temporary.s", targets["unit.o"]["dependencies"])

    def test_multiple_final_outputs_fail_instead_of_guessing(self):
        self.traces(writer_extra='openat(AT_FDCWD, "unit.d", O_WRONLY|O_CREAT, 0666) = 4\n')
        with self.assertRaisesRegex(Unsupported, "multiple final outputs"):
            execution_graph(self.folder, self.root)

    def test_numeric_directory_fd_relative_path_fails_explicitly(self):
        self.traces(reader_extra='openat(7, "another.h", O_RDONLY) = 8\n')
        with self.assertRaisesRegex(Unsupported, "numeric directory FD"):
            execution_graph(self.folder, self.root)

    def test_unfinished_clone_is_reassembled(self):
        self.traces()
        self.write("t.10", 'execve("/usr/bin/make", ["make", "app"], []) = 0\n'
                   'clone(child_stack=NULL, flags=SIGCHLD <unfinished ...>\n'
                   '<... clone resumed>) = 11\n')
        targets, _ = execution_graph(self.folder, self.root)
        self.assertIn("unit.o", targets)

    def test_split_args_preserves_commas_in_quoted_and_nested_values(self):
        args = r'AT_FDCWD, "name,\"quoted,part\".h", [1, 2], {fd=3, path="x,y"}, O_RDONLY'
        self.assertEqual(split_args(args), [
            'AT_FDCWD', r'"name,\"quoted,part\".h"', '[1, 2]',
            '{fd=3, path="x,y"}', 'O_RDONLY',
        ])

    def test_nested_unfinished_syscall_is_rejected(self):
        trace = self.write("t.10", 'openat(AT_FDCWD, "a", O_RDONLY <unfinished ...>\n'
                                   'openat(AT_FDCWD, "b", O_RDONLY <unfinished ...>\n')
        with self.assertRaisesRegex(Unsupported, "Nested unfinished"):
            trace_events(trace)

    def test_merged_unfinished_syscall_keeps_start_line(self):
        trace = self.write("t.10", 'openat(AT_FDCWD, "a", O_RDONLY <unfinished ...>\n'
                                   '<... openat resumed>) = 3\n')
        events = trace_events(trace)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["call"], "openat")
        self.assertEqual(events[0]["return"], 3)
        self.assertEqual(events[0]["line"], 1)

    def test_missing_child_trace_is_not_silently_accepted(self):
        self.traces()
        (self.folder / "t.12").unlink()
        with self.assertRaisesRegex(Unsupported, "Missing trace"):
            execution_graph(self.folder, self.root)

    def test_phony_expands_to_real_files_and_order_only_is_separate(self):
        db=self.write("db.txt", '# Files\n.PHONY: prepare\nprepare: needed.h\n'
                      'unit.o: unit.c prepare | build-dir\n# files hash-table stats:\n')
        declared=declaration_graph(db, self.root)
        self.assertNotIn("prepare", declared)
        self.assertEqual(set(declared["unit.o"]["dependencies"]), {"unit.c", "needed.h"})
        self.assertEqual(declared["unit.o"]["order_only"], ["build-dir"])

    def test_detection_finds_exact_error_edges_not_just_counts(self):
        self.traces()
        db=self.write("db.txt", '# Files\nunit.o: unit.c unused.h\n# files hash-table stats:\n')
        result=analyze(self.folder, db, self.root)
        self.assertEqual({(x["type"], x["target"], x["dependency"]) for x in result["findings"]},
                         {("MISSING", "unit.o", "needed.h"), ("REDUNDANT", "unit.o", "unused.h")})

    def test_make_database_without_files_section_is_not_an_empty_success(self):
        db=self.write("db.txt", 'unit.o: unit.c needed.h\n')
        with self.assertRaisesRegex(Unsupported, "Files section"):
            declaration_graph(db, self.root)

    def test_parent_relative_paths_normalize_but_cannot_escape_project_root(self):
        self.assertEqual(project_path("../src/unit.h", "/course/project/build", self.root),
                         "src/unit.h")
        self.assertIsNone(project_path("../../etc/passwd", "/course/project/build", self.root))
        self.assertIsNone(project_path("/course/project-other/secret.h", "/course/project/build",
                                       self.root))

class TestResumedSyscallWithoutStart(unittest.TestCase):
    """A12 E5-E7 扩展测试（选项 A）：无起点 resumed 系统调用必须显式拒绝"""

    def test_resumed_syscall_without_start_fails_explicitly(self):
        import tempfile
        from pathlib import Path
        from buildchecker.fullcheck import trace_events, Unsupported

        d = Path(tempfile.mkdtemp())
        p = d / "t.10"
        p.write_text('<... openat resumed>) = 3\n')
        with self.assertRaisesRegex(Unsupported, "Resumed syscall without start"):
            trace_events(str(p))

class TestResumedSyscallWithoutStart(unittest.TestCase):
    """A12 E5-E7 扩展测试（选项 A）：无起点 resumed 系统调用必须显式拒绝"""

    def test_resumed_syscall_without_start_fails_explicitly(self):
        import os
        import tempfile
        from pathlib import Path
        from buildchecker.fullcheck import trace_events, Unsupported

        d = Path(tempfile.mkdtemp())
        tf = d / "t.10"
        tf.write_text("<... openat resumed>) = 3\n")
        # 部分实现要求传目录，部分要求传文件；优先按现有用法传目录更稳
        try:
            with self.assertRaisesRegex(Unsupported, "Resumed syscall without start"):
                trace_events(d)
            return
        except AssertionError:
            raise
        except Exception:
            pass

        with self.assertRaisesRegex(Unsupported, "Resumed syscall without start"):
            trace_events(str(tf))


if __name__ == "__main__":
    unittest.main()
