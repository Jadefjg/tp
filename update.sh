#!/bin/bash
# 阿里云生产环境：git pull 后重启 systemd 服务（testplatform.service）。
# 当前机器已用 venv + 宿主机 MySQL/Redis 运行，不要走已失效的 docker/subnet 方案。
# 如需容器部署：DEPLOY_MODE=docker bash update.sh
set -euo pipefail

cd "$(dirname "$0")"

DEPLOY_MODE="${DEPLOY_MODE:-systemd}"
PIP_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_HOST="${PIP_HOST:-pypi.tuna.tsinghua.edu.cn}"

echo "[deploy] 拉取代码..."
if [ "${SKIP_GIT:-0}" = "1" ]; then
  echo "[deploy] 已设置 SKIP_GIT=1，跳过 git pull"
elif ! git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 pull; then
  echo "[deploy] git pull 失败（多为访问 GitHub 超时），继续使用当前目录代码"
fi

deploy_systemd() {
  local python_bin="${PYTHON_BIN:-$PWD/venv/bin/python3.8}"
  local pip_bin="${PIP_BIN:-$PWD/venv/bin/pip}"
  local service="${SERVICE_NAME:-testplatform}"

  if [ ! -x "$python_bin" ]; then
    echo "[deploy] 找不到虚拟环境: $python_bin" >&2
    exit 1
  fi

  if [ "${SKIP_PIP:-0}" = "1" ]; then
    echo "[deploy] 已设置 SKIP_PIP=1，跳过 pip install"
  else
    echo "[deploy] 安装依赖..."
    "$pip_bin" install -q -r requirements.txt -i "$PIP_INDEX" --trusted-host "$PIP_HOST"
  fi

  echo "[deploy] 重启 ${service}..."
  ensure_public_port "${TP_PORT:-8081}"
  if ! systemctl stop "$service"; then
    echo "[deploy] 正常停止超时，强制结束旧进程"
    systemctl kill -s SIGKILL "$service" >/dev/null 2>&1 || true
    sleep 1
    systemctl reset-failed "$service" >/dev/null 2>&1 || true
  fi
  systemctl start "$service"

  wait_http_ok "${TP_PORT:-8081}" "$service"
  systemctl --no-pager --full status "$service" || true
}

port_is_listening() {
  local port="$1"
  ss -ltn 2>/dev/null | grep -Eq ":${port}[[:space:]]"
}

ensure_public_port() {
  local port="$1"
  if ! command -v firewall-cmd >/dev/null 2>&1; then
    return 0
  fi
  if ! systemctl is-active --quiet firewalld; then
    return 0
  fi
  if firewall-cmd --query-port="${port}/tcp" >/dev/null 2>&1; then
    return 0
  fi
  echo "[deploy] firewalld 未放行 ${port}/tcp，正在开放..."
  firewall-cmd --permanent --add-port="${port}/tcp"
  firewall-cmd --reload
}

wait_http_ok() {
  local port="$1"
  local service="$2"
  local timeout_s="${HEALTH_TIMEOUT:-180}"
  local started now elapsed
  started="$(date +%s)"

  echo "[deploy] 健康检查（最多 ${timeout_s}s）。高负载时导入代码需要一段时间，请等待 GET /login -> 200"
  while true; do
    now="$(date +%s)"
    elapsed="$((now - started))"
    if [ "$elapsed" -ge "$timeout_s" ]; then
      echo "[deploy] ${timeout_s}s 内未就绪。最近日志：" >&2
      journalctl -u "$service" -n 40 --no-pager >&2 || true
      return 1
    fi

    if ! systemctl is-active --quiet "$service"; then
      echo "[deploy] 服务不在运行，查看 journalctl -u ${service}" >&2
      journalctl -u "$service" -n 40 --no-pager >&2 || true
      return 1
    fi

    if ! port_is_listening "$port"; then
      echo "[deploy] 等待监听 127.0.0.1:${port} ... ${elapsed}s"
      sleep 3
      continue
    fi

    if curl -fsS -o /dev/null --connect-timeout 3 --max-time 15 "http://127.0.0.1:${port}/login" 2>/dev/null; then
      echo "[deploy] GET /login -> 200（耗时 ${elapsed}s）"
      echo "[deploy] 完成。访问: http://127.0.0.1:${port}/login"
      return 0
    fi
    echo "[deploy] 端口已开，等待 HTTP 就绪 ... ${elapsed}s"
    sleep 3
  done
}

pull_base_image() {
  local tagged="$1"
  if docker image inspect "$tagged" >/dev/null 2>&1; then
    echo "[deploy] 基础镜像已存在: ${tagged}"
    return 0
  fi

  local mirrors=(
    "docker.m.daocloud.io/library/${tagged}"
    "docker.1ms.run/library/${tagged}"
    "${tagged}"
  )
  local img
  for img in "${mirrors[@]}"; do
    echo "[deploy] 尝试拉取 ${img} ..."
    if docker pull "$img"; then
      if [ "$img" != "$tagged" ]; then
        docker tag "$img" "$tagged"
      fi
      return 0
    fi
  done

  if docker image inspect python:3.11-slim-bookworm >/dev/null 2>&1; then
    echo "[deploy] 改用本机已有 python:3.11-slim-bookworm"
    PYTHON_IMAGE="python:3.11-slim-bookworm"
    return 0
  fi

  echo "[deploy] 无法拉取基础镜像，请检查 Docker 镜像加速或改用 DEPLOY_MODE=systemd" >&2
  return 1
}

deploy_docker() {
  local app_name="${APP_NAME:-tp}"
  local image_name="${IMAGE_NAME:-tp}"
  local docker_network="${DOCKER_NETWORK:-shared-infra}"
  local media_dir="${MEDIA_DIR:-/alitest/tp-master/media}"
  local tp_port="${TP_PORT:-8080}"
  local mysql_host="${MYSQL_HOST:-172.17.0.1}"
  local mysql_port="${MYSQL_PORT:-3306}"
  local mysql_user="${MYSQL_USER:-test}"
  local mysql_password="${MYSQL_PASSWORD:-test}"
  local mysql_database="${MYSQL_DATABASE:-test}"
  local redis_url="${REDIS_URL:-redis://172.17.0.1:6379/0}"
  local tp_host="${TP_HOST:-39.108.180.245:${tp_port}}"
  PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.9-slim-bullseye}"

  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi

  if ! docker network inspect "$docker_network" >/dev/null 2>&1; then
    echo "[deploy] Docker 网络不存在: ${docker_network}" >&2
    docker network ls
    exit 1
  fi

  pull_base_image "$PYTHON_IMAGE"

  echo "[deploy] 构建镜像 ${image_name}..."
  docker build --build-arg "PYTHON_IMAGE=${PYTHON_IMAGE}" -t "${image_name}" .

  mkdir -p "${media_dir}"

  if docker ps -a --format '{{.Names}}' | grep -qx "${app_name}"; then
    echo "[deploy] 停止并删除旧容器 ${app_name}..."
    docker stop "${app_name}" >/dev/null || true
    docker rm "${app_name}" >/dev/null || true
  fi

  echo "[deploy] 启动新容器..."
  docker run --restart always --name "${app_name}" -d \
    --network "${docker_network}" \
    -p "${tp_port}:${tp_port}" \
    -e TZ=Asia/Shanghai \
    -e TP_DEBUG=false \
    -e TP_PORT="${tp_port}" \
    -e TP_WORKERS=1 \
    -e TP_RUNNER_PER_WORKER=20 \
    -e TP_GENERATE_SCHEMAS=true \
    -e TP_INIT_DEBUG_DATA=false \
    -e TP_HOST="${tp_host}" \
    -e MYSQL_HOST="${mysql_host}" \
    -e MYSQL_PORT="${mysql_port}" \
    -e MYSQL_USER="${mysql_user}" \
    -e MYSQL_PASSWORD="${mysql_password}" \
    -e MYSQL_DATABASE="${mysql_database}" \
    -e REDIS_URL="${redis_url}" \
    -v "${media_dir}:/app/media" \
    "${image_name}"

  docker image prune -f >/dev/null || true
  echo "[deploy] 完成。容器状态："
  docker ps --filter "name=${app_name}" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
  echo "[deploy] 日志： docker logs -f ${app_name}"
}

case "$DEPLOY_MODE" in
  systemd) deploy_systemd ;;
  docker) deploy_docker ;;
  *)
    echo "[deploy] 未知 DEPLOY_MODE=${DEPLOY_MODE}，可选 systemd / docker" >&2
    exit 1
    ;;
esac
