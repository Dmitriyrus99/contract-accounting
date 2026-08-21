"""Run the explicit Frappe/Bench part of the release quality profile.

The caller must name a disposable or approved non-production Bench and site.
This script never reads or prints site configuration or credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

SAFE_SITE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
NON_PRODUCTION_CONFIRMATION = "I CONFIRM THIS IS A DISPOSABLE NON-PRODUCTION SITE"
EXPECTED_APPS = frozenset({"frappe", "erpnext", "contract_accounting"})
HASH_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "contract_accounting.egg-info",
        "dist",
        "node_modules",
        "output",
    }
)


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def capture(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    print(f"$ {' '.join(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout, end="", flush=True)
    return result.stdout


def tree_digest(root: Path) -> tuple[str, int]:
    """Hash path names and bytes for the exact source tree being qualified."""

    digest = hashlib.sha256()
    files = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if HASH_EXCLUDED_DIRS.intersection(relative.parts) or not path.is_file():
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        files += 1
    return digest.hexdigest(), files


def app_names(transcript: str) -> set[str]:
    return {
        line.split()[0]
        for line in transcript.splitlines()
        if line.strip() and not line.lstrip().startswith(("$", "WARN", "WARNING"))
    }


def app_versions(transcript: str) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in transcript.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] in EXPECTED_APPS:
            versions[fields[0]] = fields[1]
    return versions


def compatible_node_bin(home: Path, expected_major: str) -> Path:
    """Return the newest installed NVM Node binary for the approved major."""

    candidates: list[tuple[tuple[int, ...], Path]] = []
    for node_bin in (home / ".nvm" / "versions" / "node").glob(f"v{expected_major}.*/bin"):
        version_text = node_bin.parent.name.removeprefix("v")
        try:
            version = tuple(int(part) for part in version_text.split("."))
        except ValueError:
            continue
        candidates.append((version, node_bin))
    if not candidates:
        raise SystemExit(f"No installed NVM Node {expected_major}.x runtime")
    return max(candidates)[1]


def run_tests(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    """Stream Bench output and reject Frappe's false zero exit on failed tests."""

    print(f"$ {' '.join(command)}", flush=True)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output: list[str] = []
    assert process.stdout is not None
    with process.stdout:
        for line in process.stdout:
            print(line, end="", flush=True)
            output.append(line)
    return_code = process.wait()
    transcript = "".join(output)
    if return_code or re.search(r"(?m)^FAILED(?:\s|$)", transcript):
        raise subprocess.CalledProcessError(return_code or 1, command)
    if not re.search(r"(?m)^OK(?:\s|$)", transcript):
        raise RuntimeError("Bench test transcript has no final OK marker")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--non-production-confirmation", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    bench_root = args.bench_root.expanduser().resolve()
    source_root = args.source_root.expanduser().resolve()
    bench_candidates = (
        bench_root / "env" / "bin" / "bench",
        Path.home() / ".local" / "bin" / "bench",
    )
    bench = next((candidate for candidate in bench_candidates if candidate.is_file()), None)
    if bench is None:
        raise SystemExit(
            "Bench executable not found: "
            + ", ".join(str(candidate) for candidate in bench_candidates)
        )
    if not SAFE_SITE_RE.fullmatch(args.site):
        raise SystemExit("Site name contains unsupported characters")
    if not args.site.endswith(".localhost"):
        raise SystemExit("Bench quality gate is restricted to disposable .localhost sites")
    if args.non_production_confirmation != NON_PRODUCTION_CONFIRMATION:
        raise SystemExit("Exact non-production confirmation is required")
    if not (bench_root / "sites" / args.site).is_dir():
        raise SystemExit(f"Site directory not found: {args.site}")
    if not (source_root / "contract_accounting" / "__init__.py").is_file():
        raise SystemExit("Source root is not a contract_accounting checkout")
    compatibility_path = source_root / "runtime-compatibility.json"
    if not compatibility_path.is_file():
        raise SystemExit("Missing runtime-compatibility.json")
    compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    installed_root = (bench_root / "apps" / "contract_accounting").resolve()
    if not (installed_root / "contract_accounting" / "__init__.py").is_file():
        raise SystemExit("Bench contract_accounting app source is missing")
    source_hash, source_files = tree_digest(source_root)
    installed_hash, installed_files = tree_digest(installed_root)
    if (source_hash, source_files) != (installed_hash, installed_files):
        raise SystemExit(
            "Bench app source differs from the requested checkout: "
            f"source={source_hash}/{source_files}, installed={installed_hash}/{installed_files}"
        )
    print(f"QUALIFIED_SOURCE_SHA256={source_hash}|FILES={source_files}")

    env = os.environ.copy()
    node_bin = compatible_node_bin(Path.home(), str(compatibility["node"]))
    path_prefix = [str(node_bin), str(bench.parent)]
    env["PATH"] = os.pathsep.join([*path_prefix, env.get("PATH", "")])

    bench_python = bench_root / "env" / "bin" / "python"
    python_version = capture([str(bench_python), "--version"], cwd=bench_root, env=env).strip()
    node_version = capture(["node", "--version"], cwd=bench_root, env=env).strip()
    if not python_version.startswith(f"Python {compatibility['python']}."):
        raise SystemExit(
            f"Bench Python differs: expected {compatibility['python']}.x, actual {python_version}"
        )
    if not node_version.lstrip("v").startswith(f"{compatibility['node']}."):
        raise SystemExit(f"Node differs: expected {compatibility['node']}.x, actual {node_version}")

    bench_command = [str(bench)]
    inventory = capture([*bench_command, "--site", args.site, "list-apps"], cwd=bench_root, env=env)
    installed_apps = app_names(inventory)
    if installed_apps != EXPECTED_APPS:
        raise SystemExit(
            "Disposable site app inventory differs: "
            f"expected={sorted(EXPECTED_APPS)}, actual={sorted(installed_apps)}"
        )
    expected_versions = {app: str(compatibility[app]) for app in EXPECTED_APPS}
    actual_versions = app_versions(inventory)
    if actual_versions != expected_versions:
        raise SystemExit(
            "Disposable site versions differ from runtime compatibility manifest: "
            f"expected={expected_versions}, actual={actual_versions}"
        )
    print("NON_PRODUCTION_SENTINEL=PASS|SITE_SUFFIX=.localhost|APP_INVENTORY=EXACT")
    if args.preflight_only:
        print("BENCH_PREFLIGHT=PASS|MIGRATE_BUILD_TESTS=NOT_RUN")
        return
    run([*bench_command, "--site", args.site, "migrate"], cwd=bench_root, env=env)
    run([*bench_command, "build", "--app", "contract_accounting"], cwd=bench_root, env=env)
    run_tests(
        [
            *bench_command,
            "--site",
            args.site,
            "run-tests",
            "--app",
            "contract_accounting",
            "--skip-test-records",
        ],
        cwd=bench_root,
        env=env,
    )
    print("BENCH_QUALITY_GATE=PASS")
    print("UAT_PERFORMANCE_RESTORE_DEPLOYMENT_GATES=NOT_EVALUATED")


if __name__ == "__main__":
    main()
