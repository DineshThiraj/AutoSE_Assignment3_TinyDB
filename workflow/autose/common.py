"""Bounded inert data, immutable artifacts and controller-owned budgets."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

REPOSITORY = "DineshThiraj/AutoSE_Assignment3_TinyDB"
PIN = "edff96aeb2616402e9489d46e90a592c05565621"
DESIGN = "67c9b3c4286f598d5d415fb60433870cf63035a8"
STAGES = ("requirements", "design", "implementation", "testing", "release", "review")
MAX_BYTES = 2_000_000
ROLE_IDENTITY = {'requirements':'requirements','design':'design','implementation':'implement_test',
                 'testing':'implement_test','review':'review'}
SECRET_PATTERN = re.compile(r'(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}|\bsk-[A-Za-z0-9_-]{24,}|\bAKIA[A-Z0-9]{16}\b)')


class GateError(ValueError):
    """An absent or failed gate; never an implied approval."""


def require(condition, message):
    if not condition:
        raise GateError(message)


def digest(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def text(value, label="text", maximum=200_000):
    require(isinstance(value, str) and 0 < len(value.encode()) <= maximum, f"invalid {label}")
    require("\x00" not in value, f"NUL in {label}")
    return value


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{40}", value), "invalid commit SHA")
    return value


def json_load(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "missing/linked JSON input")
    require(path.stat().st_size <= MAX_BYTES, "JSON input too large")
    return json.loads(path.read_text())


def artifact(directory, state, outputs=None):
    """Write once. Manifest covers every file; state/outputs cannot choose paths."""
    root = Path(directory)
    require(not root.exists(), "artifact directory already exists")
    root.mkdir(parents=True)
    files = {"state.json": encoded(state) + "\n", **(outputs or {})}
    for name, value in files.items():
        require(re.fullmatch(r"[A-Za-z0-9_.-]+", name), "invalid artifact filename")
        require(name != "manifest.json", "reserved artifact filename")
        text(value, name, MAX_BYTES)
        (root / name).write_text(value)
    manifest = {name: digest((root / name).read_bytes()) for name in sorted(files)}
    (root / "manifest.json").write_text(encoded(manifest) + "\n")


def load_artifact(directory):
    root = Path(directory)
    manifest = json_load(root / "manifest.json")
    require(isinstance(manifest, dict), "invalid manifest")
    require(set(p.name for p in root.iterdir()) == set(manifest) | {"manifest.json"}, "unmanifested file")
    for name, expected in manifest.items():
        require(re.fullmatch(r"[A-Za-z0-9_.-]+", name), "manifest path")
        path = root / name
        require(path.is_file() and not path.is_symlink(), "linked artifact")
        require(path.stat().st_size <= MAX_BYTES, "oversized artifact")
        require(digest(path.read_bytes()) == expected, "artifact hash mismatch")
    state = json_load(root / "state.json")
    require(state["repository"] == REPOSITORY and state["pin"] == PIN, "state origin mismatch")
    require(digest(encoded(state["issue"])) == state["issue_hash"], "issue hash mismatch")
    return state


def budget(state, *, reserve_output=0):
    limits, used = state["limits"], state["usage"]
    require(1 <= limits["calls"] <= 24, "invalid call ceiling")
    require(used["calls"] < limits["calls"], "model call budget exhausted")
    require(used["tokens"] + reserve_output <= limits["tokens"], "token budget exhausted")
    require(time.time() - state["started_at"] <= min(limits["seconds"], 2400), "run time budget exhausted")
    require(not used.get("unknown"), "provider usage unknown; stop before another call")


def gate(state, stage, status, detail, **evidence):
    require(stage in STAGES or stage == "admission", "invalid stage")
    require(status in {"passed", "failed", "pending", "needs_clarification", "exhausted"}, "invalid status")
    entry = {"stage": stage, "status": status, "detail": detail, **evidence}
    state.setdefault("events", []).append(entry)
    state.setdefault("gates", {})[stage] = entry
    return entry


def passed(state, stage):
    require(state.get("gates", {}).get(stage, {}).get("status") == "passed", f"{stage} gate not passed")


def invalidate(state, target):
    require(target in STAGES[:4], "illegal review route")
    for stage in STAGES[STAGES.index(target):]:
        state.get("gates", {}).pop(stage, None)
    state["route"] = target


def readiness(state):
    gates = state.get("gates", {})
    approved = state.get("review", {}).get("verdict") == "APPROVE"
    return {
        "name": "MERGE_READINESS_CHECK",
        "execution_kind": state["execution_kind"],
        "gates": {s: gates.get(s, {}).get("status", "unknown") for s in STAGES},
        "head_sha": state.get("publication", {}).get("head_sha"),
        "base_sha": state.get('base_sha'),
        "published_tree_sha": state.get('publication',{}).get('tree_sha'),
        "tested_source_hash": state.get('tested_source_hash'),
        "source_hash_matches_tests": digest(encoded(state.get('source',{}))) == state.get('tested_source_hash'),
        "test_cases": {k:state.get('execution',{}).get(k) for k in ('case_count','baseline_cases','new_cases')},
        "ac_test_map": state.get('test_map',{}),
        "unresolved_findings": state.get('review',{}).get('findings',[]),
        "secret_pattern_scan": 'passed' if state.get('source') and not SECRET_PATTERN.search(encoded(state['source'])) else 'unknown/failed',
        "ci": state.get("publication", {}).get("ci", "unknown"),
        "review_verdict": state.get("review", {}).get("verdict", "unknown"),
        "rounds": state.get("round", 0),
        "hidden_tests": "unknown; separate private evaluation required",
        "human_decision": "pending",
        "automated_gates_satisfied": state['execution_kind'] == 'hosted' and all(gates.get(s, {}).get("status") == "passed" for s in STAGES) and approved,
        "merge_authorized": False,
    }
