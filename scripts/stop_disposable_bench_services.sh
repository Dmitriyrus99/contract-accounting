#!/usr/bin/env bash
set -euo pipefail

stop_exact_process() {
	local pid_file=$1
	local expected=$2
	if [[ ! -f "$pid_file" ]]; then
		return
	fi
	local pid
	pid=$(<"$pid_file")
	if [[ ! "$pid" =~ ^[0-9]+$ ]] || [[ ! -r "/proc/$pid/cmdline" ]]; then
		return
	fi
	local command_line
	command_line=$(tr '\0' ' ' <"/proc/$pid/cmdline")
	if [[ "$command_line" != *"$expected"* ]]; then
		echo "Refusing to stop unexpected process $pid from $pid_file" >&2
		exit 1
	fi
	kill "$pid"
	for _attempt in $(seq 1 30); do
		if ! kill -0 "$pid" 2>/dev/null; then
			return
		fi
		sleep 1
	done
	echo "Process $pid did not stop cleanly." >&2
	exit 1
}

stop_exact_process /home/rus/contract-accounting-bench/config/pids/redis_queue.pid "redis-server 127.0.0.1:11000"
stop_exact_process /home/rus/contract-accounting-bench/config/pids/redis_cache.pid "redis-server 127.0.0.1:13000"
stop_exact_process /home/rus/contract-accounting-mariadb/run/mariadb.pid mariadbd

if ss -ltn | grep -Eq ':(3317|13000|11000) '; then
	echo "One or more disposable service ports remain open." >&2
	ss -ltn | grep -E ':(3317|13000|11000) ' >&2
	exit 1
fi

echo "DISPOSABLE_BENCH_SERVICES=STOPPED"
