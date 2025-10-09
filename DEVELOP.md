# AI Agent時代のWebアプリケーション開発環境


Docker/Dockercompose/Devcontainer
uv + Ruff（Python側）
fnm + pnpm + Turbopack + Biome（Next.js側）
TinyTeX（LaTeX系ツール）+ require package
postgresql 

# フロントエンド インストール手順

```bash
# これをシェルの初期化ファイルに追加します。例えば、Bashを使用している場合は以下のようにします。
echo 'eval "$(fnm env)"' >> ~/.bashrc
```

## fnmの使用方法

```bash
# Node.jsのバージョンをインストールします。
fnm list-remote # 利用可能なNode.jsのバージョンを表示
fnm use -y v24.1.0 # 指定したバージョンを使用 .node-version ファイルがある場合は自動的にそのバージョンを使用します
fnm current # 現在使用しているNode.jsのバージョンを表示
```

## pnpmのインストール
frontディレクトリで
```bash
# pnpmをインストールします。
npm install -g pnpm@latest-10
pnpm install 
```


## フロントエンドのインストール
```bash 
npx create-next-app@latest front --disable-git 
```

# バックエンドインストール手順 (uv)

git initが起こらないようにする。

```bash
uv python install 3.11
uv python pin 3.11
uv init ai_agent
``` 

uvのシェル補完を有効にする
```bash 
echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
```


## pythonの構造作成
git init  が起こらないように作成

```bash 
uv init back --vcs none  --package  
```

## バックエンドのインストール

backディレクトリに移動して、DjangoとDjango REST frameworkをインストールします。
```bash
uv sync
```

backエンドでインタプリンタとシンタックスハイライトが動作しなければ、コマンドパレットから「Python:Select interpreter」を実行します。


あとでdevconatainer.jsonに追加してなにもしなくても動くようにする。


