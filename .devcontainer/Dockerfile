FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# 環境変数でタイムゾーン設定を自動化
ENV DEBIAN_FRONTEND=noninteractive

# curlをダウンロードする
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    build-essential \
    curl \
    dvisvgm \
    && add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update
# ffmpegを入れる
RUN apt-get install -y xz-utils
RUN wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz \
    && tar xvf ./ffmpeg-git-amd64-static.tar.xz \
    && cp ./ffmpeg*amd64-static/ffmpeg /usr/local/bin/ 



RUN apt install -y cmake pkg-config libcairo2-dev libgirepository1.0-dev build-essential libpangocairo-1.0-0 libpango1.0-dev libcairo2-dev xdg-utils


# --------------------------------------------------
# TeX Live Minimal（LaTeX環境）
# --------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-base texlive-latex-base texlive-latex-extra texlive-fonts-recommended latexmk && \
    rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# uv（Pythonオールインマネージャー）
# --------------------------------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | bash && \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> /etc/bash.bashrc

# ---- fnmのみインストール ----
RUN curl -fsSL https://fnm.vercel.app/install | bash -s -- --install-dir "/usr/local/share/fnm" --skip-shell

# ---- PATHを通す＆bash起動時にfnm envを自動読み込み ----
RUN ln -sf /usr/local/share/fnm/fnm /usr/local/bin/fnm && \
    echo 'export FNM_DIR="/usr/local/share/fnm"' >> /etc/profile.d/fnm.sh && \
    echo 'export PATH="$FNM_DIR:$PATH"' >> /etc/profile.d/fnm.sh && \
    echo 'eval "$(fnm env)"' >> /etc/profile.d/fnm.sh

# ---- シェルをlogin bashに変更して環境を読む ----
SHELL ["/bin/bash", "-l", "-c"]
CMD ["bash"]