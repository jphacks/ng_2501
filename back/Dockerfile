# ============================================
# Backend Dockerfile (Cloudflare Tunnel対応)
# ============================================
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# manim と動画生成に必要なシステムパッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    # ビルドツール
    build-essential \
    curl \
    ca-certificates \
    git \
    pkg-config \
    cmake \
    wget \
    xz-utils \
    # manim 描画ライブラリ
    libcairo2-dev \
    libgirepository1.0-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*


# TeX Live（必要最小限）
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-full texlive-lang-cjk && \
    rm -rf /var/lib/apt/lists/*

# ffmpeg 静的バイナリのインストール
RUN wget -q https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz \
    && tar xf ffmpeg-git-amd64-static.tar.xz \
    && cp ffmpeg-git-*-amd64-static/ffmpeg /usr/local/bin/ \
    && cp ffmpeg-git-*-amd64-static/ffprobe /usr/local/bin/ \
    && rm -rf ffmpeg-git-*-amd64-static* ffmpeg-git-amd64-static.tar.xz

# uv のインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /back

# アプリケーションコードをコピー
COPY . .

# 依存関係をインストール
RUN uv sync --frozen --no-dev

# 仮想環境の PATH を設定
# PYTHONPATH=/ により back.app... のインポートを可能にする
ENV PATH="/back/.venv/bin:${PATH}" \
    VIRTUAL_ENV="/back/.venv" \
    PYTHONPATH="/"

# media ディレクトリを作成
RUN mkdir -p /back/media

# ポート設定
EXPOSE 8080

# uvicorn でサーバー起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
