"""Run the explicit Frappe/Bench part of the release quality profile.

The caller must name a disposable or approved non-production Bench and site.
This script never reads or prints site configuration or credentials.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

SAFE_SITE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


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
    parser.add_argument("--site", required=True)
    args = parser.parse_args()

    bench_root = args.bench_root.expanduser().resolve()
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
    if not (bench_root / "sites" / args.site).is_dir():
        raise SystemExit(f"Site directory not found: {args.site}")

    env = os.environ.copy()
    node_bins = sorted((Path.home() / ".nvm" / "versions" / "node").glob("v*/bin"))
    path_prefix = [str(bench.parent)]
    if node_bins:
        path_prefix.insert(0, str(node_bins[-1]))
    env["PATH"] = os.pathsep.join([*path_prefix, env.get("PATH", "")])

    bench_command = [str(bench)]
    run([*bench_command, "--site", args.site, "list-apps"], cwd=bench_root, env=env)
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
