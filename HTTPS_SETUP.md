# GCE本番環境でのHTTPS化セットアップガイド

このガイドでは、Google Compute Engine (GCE)上でフロントエンド（Next.js）とバックエンド（FastAPI）をHTTPS化する手順を説明します。

## 前提条件

1. GCEインスタンスが起動していること
2. ドメイン `ani-math.jp` のDNS Aレコードが GCE インスタンスのIPアドレスに設定されていること
3. GCE のファイアウォールで以下のポートが開放されていること：
   - ポート 80 (HTTP)
   - ポート 443 (HTTPS)
4. Docker と Docker Compose がインストールされていること

## アーキテクチャ

```
                       ┌─────────────┐
                       │   Nginx     │
                       │  (Reverse   │
                       │   Proxy)    │
                       └──────┬──────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         https://ani-math.jp/          https://ani-math.jp/api/
              │                               │
      ┌───────▼────────┐            ┌────────▼────────┐
      │   Frontend     │            │    Backend      │
      │   (Next.js)    │            │    (FastAPI)    │
      │   Port: 3000   │            │    Port: 8000   │
      └────────────────┘            └─────────────────┘
```

## セットアップ手順

### 1. リポジトリをGCEにクローン

```bash
# GCEインスタンスにSSH接続
gcloud compute ssh your-instance-name

# リポジトリをクローン
git clone <repository-url>
cd ai_agent
git checkout sys/https_readme  # 本番環境用ブランチ
```

### 2. 環境変数の設定（オプション）

必要に応じて環境変数を設定します：

```bash
# .env ファイルを作成
cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:postgres@db:5432/devdb
PYTHONPATH=/workspaces/ai_agent
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://ani-math.jp/api
EOF
```

### 3. 初期起動（HTTPのみ - テスト用）

まず、証明書なしでサービスが起動するか確認します：

```bash
# 一時的にHTTPのみで起動（nginx設定を調整）
docker compose up -d app frontend db

# ログを確認
docker compose logs -f app
docker compose logs -f frontend

# 動作確認後、停止
docker compose down
```

### 4. Let's Encrypt証明書の取得とHTTPS化

**重要**: このステップを実行する前に、ドメインのDNS設定が完了していることを確認してください。

```bash
# 初期化スクリプトに実行権限を付与（既に実行済みの場合はスキップ）
chmod +x init-letsencrypt.sh

# Let's Encrypt証明書を取得
./init-letsencrypt.sh
```

このスクリプトは以下を自動的に行います：
1. ダミー証明書の生成（Nginxの初回起動用）
2. Nginxの起動
3. Let's EncryptからSSL証明書を取得
4. 証明書の自動更新設定

### 5. 全サービスの起動

```bash
# すべてのサービスを起動
docker compose up -d

# ログを確認
docker compose logs -f
```

### 6. 動作確認

ブラウザで以下のURLにアクセスして動作を確認：

- **フロントエンド**: https://ani-math.jp/
- **バックエンドAPI**: https://ani-math.jp/api/docs (FastAPIのSwagger UI)

## 証明書の自動更新

証明書は90日間有効です。`certbot` サービスが自動的に証明書の更新を行います（12時間ごとにチェック）。

手動で更新する場合：

```bash
docker compose run --rm certbot renew
docker compose exec nginx nginx -s reload
```

## トラブルシューティング

### 証明書取得に失敗する場合

1. DNSの設定を確認：
```bash
dig ani-math.jp
# GCEインスタンスのIPアドレスが返ってくることを確認
```

2. ファイアウォールの確認：
```bash
# GCEのファイアウォールルールを確認
gcloud compute firewall-rules list
```

3. ステージング環境でテスト：
`init-letsencrypt.sh` の `STAGING=1` に変更してテスト証明書で試す

### Nginxが起動しない場合

```bash
# Nginxの設定をテスト
docker compose exec nginx nginx -t

# エラーログを確認
docker compose logs nginx
```

### フロントエンドまたはバックエンドに接続できない場合

```bash
# 各サービスのログを確認
docker compose logs frontend
docker compose logs app

# ネットワークの確認
docker compose exec nginx ping frontend
docker compose exec nginx ping app
```

## メンテナンス

### サービスの再起動

```bash
# すべてのサービスを再起動
docker compose restart

# 特定のサービスのみ再起動
docker compose restart nginx
docker compose restart app
docker compose restart frontend
```

### ログの確認

```bash
# すべてのログ
docker compose logs -f

# 特定のサービスのログ
docker compose logs -f nginx
docker compose logs -f app
docker compose logs -f frontend
```

### データベースのバックアップ

```bash
# データベースのバックアップ
docker compose exec db pg_dump -U postgres devdb > backup_$(date +%Y%m%d_%H%M%S).sql

# リストア
cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T db psql -U postgres devdb
```

## セキュリティに関する注意事項

1. **メールアドレスの設定**: `init-letsencrypt.sh` の `EMAIL` を適切な管理者メールアドレスに変更してください
2. **データベースパスワード**: 本番環境では `docker-compose.yml` のPostgreSQLパスワードを強力なものに変更してください
3. **環境変数**: 機密情報は環境変数や `.env` ファイルで管理し、Gitにコミットしないでください
4. **ファイアウォール**: 必要最小限のポート（80, 443）のみ開放してください

## ファイル構成

```
.
├── docker-compose.yml          # メインのDocker Compose設定
├── Dockerfile                  # バックエンド用Dockerfile
├── front/
│   ├── Dockerfile             # フロントエンド用Dockerfile
│   └── next.config.js         # Next.js設定（standalone有効）
├── nginx/
│   ├── nginx.conf             # Nginxメイン設定
│   └── conf.d/
│       └── app.conf           # アプリケーション用Nginx設定
├── init-letsencrypt.sh        # Let's Encrypt初期化スクリプト
└── certbot/                   # 証明書ディレクトリ（自動生成）
    ├── conf/                  # Let's Encrypt設定と証明書
    └── www/                   # ACME challengeファイル
```

## 参考資料

- [Let's Encrypt ドキュメント](https://letsencrypt.org/docs/)
- [Certbot ドキュメント](https://certbot.eff.org/docs/)
- [Nginx ドキュメント](https://nginx.org/en/docs/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)


## 変更方法

再度ビルドすればOKです。

```bash