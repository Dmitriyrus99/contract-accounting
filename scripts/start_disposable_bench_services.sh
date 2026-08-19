#!/usr/bin/env bash
set -euo pipefail

bench_root=/home/rus/contract-accounting-bench
database_root=/home/rus/contract-accounting-mariadb

mkdir -p "$database_root/run" "$bench_root/config/pids" "$bench_root/logs"

if ! ss -ltn | grep -q ':3317 '; then
	nohup mariadbd \
		--no-defaults \
		--datadir="$database_root/data" \
		--socket="$database_root/run/mariadb.sock" \
		--port=3317 \
		--bind-address=127.0.0.1 \
		--pid-file="$database_root/run/mariadb.pid" \
		--log-error="$database_root/mariadb.log" \
		>"$database_root/nohup.log" 2>&1 &
fi

if ! ss -ltn | grep -q ':13000 '; then
	nohup redis-server "$bench_root/config/redis_cache.conf" \
		>"$bench_root/logs/redis-cache.log" 2>&1 &
fi

if ! ss -ltn | grep -q ':11000 '; then
	nohup redis-server "$bench_root/config/redis_queue.conf" \
		>"$bench_root/logs/redis-queue.log" 2>&1 &
fi

for _attempt in $(seq 1 30); do
	open_ports=$(ss -ltn | grep -Ec ':(3317|13000|11000) ' || true)
	if [[ "$open_ports" -eq 3 ]]; then
		ss -ltn | grep -E ':(3317|13000|11000) '
		exit 0
	fi
	sleep 1
done

echo "Disposable Bench services did not open all expected ports." >&2
exit 1
