"""E4 骨架的单元测试。E5/E6 实现方法后，在这里继续添加测试。"""
from buildchecker import __version__
from buildchecker.cli import build_parser, main
from buildchecker.smoke import files_opened


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == f"buildchecker {__version__}"


def test_smoke_default_fixture():
    assert build_parser().parse_args(["smoke"]).fixture == "fixtures/md-rd"


def test_files_opened_matches_relative_and_absolute_paths():
    trace = "\n".join([
        '101 openat(AT_FDCWD, "config.h", O_RDONLY|O_NOCTTY) = 4',
        '101 openat(AT_FDCWD, "/tmp/x/config.h", O_RDONLY) = 5',
        '101 newfstatat(AT_FDCWD, "unused.h", {st_mode=S_IFREG|0644, ...}, 0) = 0',
        '101 openat(AT_FDCWD, "myconfig.h", O_RDONLY) = 6',
    ])
    assert len(files_opened(trace, "config.h")) == 2
    assert files_opened(trace, "unused.h") == []
