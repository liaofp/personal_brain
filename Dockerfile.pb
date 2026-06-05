FROM python:3.11-slim
WORKDIR /pb
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1
    PYTHONDONTWRITEBYTECODE=1

# 🏆 进化点 1：必须在镜像内安装 git 和 openssh，否则大模型无法 commit 和 push
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    openssh-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 🏆 进化点 2：允许大模型动态安装新依赖（通过清华源）
RUN pip3 install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    sqlalchemy==2.0.49 fastapi uvicorn pydantic pytest docker

# 为了让大模型能够调用挂载进来的 docker 命令行，我们需要在容器内装一个 docker 客户端
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-24.0.7.tgz | tar -xz -C /usr/local/bin --strip-components=1 docker/docker

# 必须维持 root 权限，因为大模型需要写操作、调用 git 以及通过 socket 通信
USER root