import pytest
from codesync.core.exclusion_filter import ExclusionFilter


def test_excludes_git_directory():
    f = ExclusionFilter([".git/"])
    assert f.is_excluded(".git/config")
    assert f.is_excluded(".git/HEAD")


def test_excludes_pyc_extension():
    f = ExclusionFilter(["*.pyc"])
    assert f.is_excluded("module/file.pyc")
    assert not f.is_excluded("module/file.py")


def test_excludes_node_modules():
    f = ExclusionFilter(["node_modules/"])
    assert f.is_excluded("node_modules/express/index.js")
    assert not f.is_excluded("src/node_module.py")


def test_excludes_pycache():
    f = ExclusionFilter(["__pycache__/"])
    assert f.is_excluded("app/__pycache__/module.cpython-311.pyc")


def test_no_patterns_excludes_nothing():
    f = ExclusionFilter([])
    assert not f.is_excluded("any/file.txt")
    assert not f.is_excluded(".git/config")


def test_windows_backslash_path():
    f = ExclusionFilter(["*.pyc", "__pycache__/"])
    # Windows-style paths with backslashes should still match
    assert f.is_excluded("app\\__pycache__\\module.pyc")


def test_multiple_patterns():
    f = ExclusionFilter([".git/", "*.log", "node_modules/", ".env"])
    assert f.is_excluded(".git/HEAD")
    assert f.is_excluded("app/debug.log")
    assert f.is_excluded("node_modules/react/index.js")
    assert f.is_excluded(".env")
    assert not f.is_excluded("src/main.py")
