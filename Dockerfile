# 本番環境用
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04
ENV DEBIAN_FRONTEND=noninteractive

# ベース: 必要パッケージをまとめて導入（python/pip/venv もここで）
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
      software-properties-common \
      build-essential \
      curl \
      ca-certificates \
      git \
      pkg-config \
      cmake \
      libcairo2-dev \
      libgirepository1.0-dev \
      libpango1.0-dev \
      libpangocairo-1.0-0 \
      xdg-utils \
      dvisvgm \
      xz-utils \
      python3 \
      python3-pip \
      python3-venv && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    rm -rf /var/lib/apt/lists/*

# ffmpeg（静的ビルド）
RUN wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz \
    && tar xvf ./ffmpeg-git-amd64-static.tar.xz \
    && cp ./ffmpeg*amd64-static/ffmpeg /usr/local/bin/ \
    && rm -rf ffmpeg*amd64-static* ffmpeg-git-amd64-static.tar.xz

# TeX Live（必要最小限）
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-base texlive-latex-base texlive-latex-extra texlive-fonts-recommended latexmk && \
    rm -rf /var/lib/apt/lists/*

# uv を導入（root の ~/.local/bin/uv に入る）
RUN curl -LsSf https://astral.sh/uv/install.sh | bash
# uv の PATH を確実に通す（ログイン/非ログイン両対応）
ENV PATH="/root/.local/bin:${PATH}"
RUN echo 'export PATH="$HOME/.local/bin:$PATH"' >> /etc/bash.bashrc

# fnm 導入（Node は runtime で fnm use する想定）
RUN curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "/usr/local/share/fnm" --skip-shell && \
    ln -sf /usr/local/share/fnm/fnm /usr/local/bin/fnm && \
    echo 'export FNM_DIR="/usr/local/share/fnm"' >> /etc/profile.d/fnm.sh && \
    echo 'export PATH="$FNM_DIR:$PATH"' >> /etc/profile.d/fnm.sh && \
    echo 'eval "$(fnm env)"' >> /etc/profile.d/fnm.sh

# --- ここから本番(prod)ビルドのための修正 ---

# 作業ディレクトリ（compose の volume と一致させる）
WORKDIR /workspaces/ai_agent

# 1. プロジェクトの全ファイル(.dockerignoreを除く)を WORKDIR にコピーします
#    これが無いと、setup.sh や back/ ディレクトリが見つからずクラッシュします
COPY . .

# --- 修正ここまで ---


# ログインシェルにして /etc/profile.d を確実に読む
SHELL ["/bin/bash", "-l", "-c"]
# CMDは docker-compose.prod.yml の command で上書きされます
CMD ["bash"]

