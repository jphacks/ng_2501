# AI Agent時代のWebアプリケーション開発環境

## githubの使い方

CI/CDを利用するためデフォルトブランチはdevelopにしている。
mainブランチはリリース用に使う。動くまでがdevelopブランチで、動いたらmainにマージする。

## 開発方法

developブランチをチェックアウトして、そこから新しいブランチを切って開発する。
プルリクエストを作成して、レビューを受けてからdevelopにマージする。
プルリクエストは必ずレビューを受けること。自分でマージしないこと。
レビューは最低1人以上に依頼すること。自分で承認しないこと。

## 開発環境の要約

令和最新最速の開発環境を提供する。

Docker/Dockercompose/Devcontainer
uv + Ruff（Python側）
fnm + pnpm + Turbopack + Biome（Next.js側）
TinyTeX（LaTeX系ツール）+ require package
postgresql 

# インストール手順書　

以下の手順に従って開発環境はセットアップされている。
ただしこれは全てdevcontainer.jsonに組み込まれているので、devcontainerを使う場合はこの手順を踏む必要はない。

## フロントエンド インストール手順

```bash
# これをシェルの初期化ファイルに追加します。例えば、Bashを使用している場合は以下のようにします。
echo 'eval "$(fnm env)"' >> ~/.bashrc
```

### fnmの使用方法

```bash
# Node.jsのバージョンをインストールします。
fnm list-remote # 利用可能なNode.jsのバージョンを表示
fnm use -y v24.1.0 # 指定したバージョンを使用 .node-version ファイルがある場合は自動的にそのバージョンを使用します
fnm current # 現在使用しているNode.jsのバージョンを表示
```

### pnpmのインストール
frontディレクトリで
```bash
# pnpmをインストールします。
npm install -g pnpm@latest-10
pnpm install 
```


### フロントエンドのインストール
```bash 
npx create-next-app@latest front --disable-git 
```

## バックエンドインストール手順 (uv)

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


### pythonの構造作成
git init  が起こらないように作成

```bash 
uv init back --vcs none

```

### バックエンドのインストール

backディレクトリに移動して、DjangoとDjango REST frameworkをインストールします。
```bash
uv sync
```

backエンドでインタプリンタとシンタックスハイライトが動作しなければ、コマンドパレットから「Python:Select interpreter」を実行します。


あとでdevconatainer.jsonに追加してなにもしなくても動くようにする。

### [重要] バックエンドの起動

バックエンドを起動するには、backディレクトリで以下のコマンドを実行します。


```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```


# デプロイ

## フロントエンド

Vercelにより、CI/CDを統合したデプロイを行う。