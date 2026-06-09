# 阶段 1：UV 工具提供方
FROM crpi-2fu2kfwgnevmjwlu.cn-beijing.personal.cr.aliyuncs.com/openclaw_gateway/uv:latest AS uv_provider

# 阶段 2：最终运行环境
FROM crpi-2fu2kfwgnevmjwlu.cn-beijing.personal.cr.aliyuncs.com/openclaw_gateway/python:3.12-slim

WORKDIR /workspace

# 复制 UV 二进制（这层极少变动，缓存命中率高）
COPY --from=uv_provider /uv /usr/local/bin/uv
COPY --from=uv_provider /uvx /usr/local/bin/uvx

# 系统依赖层（这层极少变动）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# ✅ 关键改进：仅预装"已知稳定的基础框架依赖"
# 将 pyproject.toml 和 uv.lock 单独 COPY，利用 Docker 层缓存：
# 只有当 pyproject.toml 或 uv.lock 发生变化时，这一层才会重新执行
# 在 OpenClaw 改进业务逻辑代码（非依赖）时，这层完全命中缓存，启动极快
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project

# 环境变量配置
ENV UV_PROJECT_ENVIRONMENT=/workspace/.venv
ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONPATH=/workspace