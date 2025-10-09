#!/usr/bin/env bash
set -euxo pipefail

echo "DevContainer 環境セットアップ開始: $(date)"

# ---------- 共通設定 ----------
cd /workspaces/ai_agent

# uv 補完設定（重複を避けて追加）
if ! grep -q 'uv generate-shell-completion' ~/.bashrc; then
  echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
fi

# ---------- Backend: Python ----------
if [ -d "back" ]; then
  echo "🐍 Python Backend Setup 開始..."
  cd back

  # 依存関係を同期
  if command -v uv &> /dev/null; then
    uv sync
  else
    echo "uv が見つかりません。pip 経由で暫定インストールします。"
    pip install uv
    uv sync
  fi
  cd ..
else
  echo "back ディレクトリが見つかりません。スキップします。"
fi

# ---------- Frontend: Node.js ----------
if [ -d "front" ]; then
  echo "Frontend Setup 開始..."
  cd front

  # fnm 環境を有効化
  if command -v fnm &> /dev/null; then
    eval "$(fnm env)"
    fnm install v24.1.0 || true
    fnm use -- v24.1.0 
  else
    echo "fnm が見つかりません。NPM経由でNodeをセットアップします。"
    curl -fsSL https://fnm.vercel.app/install | bash
    source ~/.bashrc
    fnm install v24.1.0
    fnm use v24.1.0 -y
  fi

  # pnpm のインストール（グローバル）
  if ! command -v pnpm &> /dev/null; then
    echo "pnpm をインストール中..."
    npm install -g pnpm@latest-10
  fi

  # 依存関係インストール
  pnpm install
  cd ..
else
  echo "front ディレクトリが見つかりません。スキップします。"
fi

# ---------- Summary ----------
echo "すべてのセットアップが完了しました！"
echo "Python / Node / pnpm / uv / fnm が自動構築されました。"
