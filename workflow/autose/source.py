"""Read the genuine pinned tree and validate inert replacement proposals."""
from __future__ import annotations

import ast
import difflib
import re
import subprocess
from pathlib import Path, PurePosixPath

from .common import PIN, SECRET_PATTERN, digest, encoded, require, text


def allowed(path, kind):
    require(isinstance(path, str) and "\\" not in path and "\x00" not in path, "invalid patch path")
    p = PurePosixPath(path)
    require(not p.is_absolute() and str(p) == path and all(x not in (".", "..") for x in p.parts), "patch traversal")
    pattern = r"tinydb/[a-z_]+\.py" if kind == "implementation" else r"tests/test_autose_[a-z0-9_]+\.py"
    require(re.fullmatch(pattern, path), "patch path outside allowlist")


def snapshot(repository):
    repo = str(repository)
    names = subprocess.check_output(["git", "-C", repo, "ls-tree", "-r", "--name-only", PIN, "tinydb", "tests"], text=True).splitlines()
    source = {}
    for name in names:
        if not name.endswith(".py"):
            continue
        raw = subprocess.check_output(["git", "-C", repo, "show", f"{PIN}:{name}"])
        require(len(raw) <= 200_000 and b'\x00' not in raw, 'invalid pinned source file')
        source[name] = raw.decode()
    require(len(source) == 19 and 'tinydb/table.py' in source and 'tests/conftest.py' in source, "pinned source incomplete")
    return source


def replacements(base, changes, kind, *, baseline):
    require(isinstance(changes, dict) and 1 <= len(changes) <= 8, "invalid edit set")
    result = dict(base)
    for path, content in changes.items():
        allowed(path, kind)
        text(content, path, 150_000)
        require(not SECRET_PATTERN.search(content), 'credential-like material in proposed file')
        if kind == "implementation":
            require(path in baseline, "cannot create unknown TinyDB module")
        else:
            require(path not in baseline, "baseline test replacement forbidden")
        result[path] = content
    require(sum(len(v.encode()) for v in result.values()) <= 800_000, "source snapshot too large")
    for path, original in baseline.items():
        if path.startswith("tests/"):
            require(result.get(path) == original, "baseline test modified")
    return result


def diff(baseline, source):
    lines = []
    for path in sorted(set(baseline) | set(source)):
        if baseline.get(path) != source.get(path):
            lines.extend(difflib.unified_diff(baseline.get(path, "").splitlines(True), source.get(path, "").splitlines(True), fromfile="a/" + path if path in baseline else "/dev/null", tofile="b/" + path))
    return "".join(lines)


def materialize(source, destination):
    root = Path(destination)
    require(not root.exists(), "source destination exists")
    root.mkdir(parents=True)
    for path, content in source.items():
        # Snapshots contain Python files from the tracked pin and allowlisted edits only.
        require(re.fullmatch(r"(?:tinydb|tests)/[a-zA-Z0-9_/]+\.py", path), "snapshot path")
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)


def source_hash(source):
    return digest(encoded(source))


def tests_cover(source, baseline, mapping, ac_ids):
    require(isinstance(mapping, dict) and set(mapping) == set(ac_ids), "each AC requires a test mapping")
    for criterion, node in mapping.items():
        text(node, "test node", 300)
        parts = node.split("::")
        require(len(parts) == 2, "test mapping must name a top-level test function")
        path, function = parts
        allowed(path, "testing")
        require(path in source and path not in baseline, "mapped test missing/new test required")
        tree = ast.parse(source[path])
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function]
        require(function.startswith("test_") and len(functions) == 1, "test function not found")
        fn = functions[0]
        require(any(isinstance(n, ast.Assert) for n in ast.walk(fn)), "mapped test has no assertion")
        require(not any(isinstance(n, ast.Attribute) and n.attr in {"skip", "skipif", "xfail"} for n in ast.walk(fn)), "mapped test suppressed")
    return True
