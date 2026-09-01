#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time
from urllib.parse import urlparse


def wait_tcp(host, port, timeout=90, name=''):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), 2):
                print(f'[entrypoint] {name or host}:{port} is ready')
                return
        except OSError as exc:
            last_error = exc
            time.sleep(1)
    raise SystemExit(f'[entrypoint] timeout waiting for {name or host}:{port}: {last_error}')


mysql_host = os.getenv('MYSQL_HOST', 'mysql')
mysql_port = os.getenv('MYSQL_PORT', '3306')
wait_tcp(mysql_host, mysql_port, name='mysql')

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
parsed = urlparse(redis_url)
wait_tcp(parsed.hostname or 'redis', parsed.port or 6379, name='redis')
PY

exec python app.py
