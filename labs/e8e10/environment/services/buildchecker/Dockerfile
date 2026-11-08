# E5-E7 A组 BuildChecker。构建上下文为仓库根目录。
# 使用 Docker 内置解析器，避免额外下载 docker/dockerfile 语法镜像。
ARG BASE_IMAGE=m.daocloud.io/docker.io/library/python:3.13-slim@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
FROM ${BASE_IMAGE}

ENV LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 固定基础镜像采用 Debian DEB822 源配置；保留发行版及签名校验。
RUN sed -i \
      -e 's|https\?://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
      -e 's|https\?://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
      -e 's|https\?://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' \
      /etc/apt/sources.list.d/debian.sources \
 && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update \
 && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 install -y --no-install-recommends gcc make libc6-dev strace git \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package}=${Version}\n' gcc make libc6-dev strace git > /opt/toolchain.lock \
 && echo "python3=$(python3 -c 'import platform; print(platform.python_version())')" >> /opt/toolchain.lock \
 && echo "arch=$(dpkg --print-architecture)" >> /opt/toolchain.lock

COPY requirements-dev.lock /tmp/requirements-dev.lock
RUN python3 -m pip install \
      --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
      --timeout 60 --retries 3 \
      --no-cache-dir --require-hashes -r /tmp/requirements-dev.lock \
 && python3 -m pip freeze | sed 's/^/pip:/' >> /opt/toolchain.lock

RUN useradd --create-home --uid 10001 app \
 && install -d -o app -g app /app
WORKDIR /app
COPY --chown=app:app services/buildchecker/ /app/
COPY --chown=app:app fixtures/ /app/fixtures/
USER app

CMD ["python3", "-m", "buildchecker", "--help"]
