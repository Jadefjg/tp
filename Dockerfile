# 国内默认走 DaoCloud 代理，避免直连 Docker Hub 超时。
# 覆盖示例: docker build --build-arg PYTHON_IMAGE=python:3.11-slim-bookworm .
ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.9-slim-bullseye
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai \
    TP_DEBUG=false \
    TP_PORT=8081 \
    TP_WORKERS=1 \
    TP_GENERATE_SCHEMAS=true

WORKDIR /app

RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i 's/deb.debian.org/mirrors.aliyun.com/g; s/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list; \
    fi; \
    if [ -d /etc/apt/sources.list.d ]; then \
      find /etc/apt/sources.list.d -type f -exec sed -i 's/deb.debian.org/mirrors.aliyun.com/g; s/security.debian.org/mirrors.aliyun.com/g' {} +; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libssl-dev \
        default-libmysqlclient-dev \
        tzdata; \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime; \
    echo $TZ > /etc/timezone; \
    rm -rf /var/lib/apt/lists/*

ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -U pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
        -i ${PIP_INDEX} --trusted-host pypi.tuna.tsinghua.edu.cn

COPY . /app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /app/media/casedata /app/media/casefile /app/media/taskfile/videos \
    && apt-get purge -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8081

ENTRYPOINT ["/entrypoint.sh"]
