# 阶段 1：利用您指定的 UV 私有镜像作为工具提供方
FROM crpi-2fu2kfwgnevmjwlu.cn-beijing.personal.cr.aliyuncs.com/openclaw_gateway/uv:latest AS uv_provider

# 阶段 2：利用您指定的 Python 3.12 私有镜像构造最终运行环境
FROM crpi-2fu2kfwgnevmjwlu.cn-beijing.personal.cr.aliyuncs.com/openclaw_gateway/python:3.12-slim

WORKDIR /workspace/src

# 从 uv 镜像中将官方二进制可执行文件强行复制到本机的系统路径中
COPY --from=uv_provider /uv /usr/local/bin/uv
COPY --from=uv_provider /uvx /usr/local/bin/uvx

# 设置环境变量，强制 UV 使用项目内挂载的 .venv 虚拟环境
ENV UV_PROJECT_ENVIRONMENT=/workspace/src/.venv
ENV PATH="/workspace/src/.venv/bin:$PATH"

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*