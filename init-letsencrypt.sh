#!/bin/bash

# GCEセットアップのREADMEに従い、
# sudo DOMAIN=example.com EMAIL=your-email@example.com ./init-letsencrypt.sh
# のように実行してください。

# 変数が設定されていない場合はエラー
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "エラー: DOMAIN と EMAIL 環境変数を設定してください。"
  echo "例: sudo DOMAIN=example.com EMAIL=your-email@example.com $0"
  exit 1
fi

# v1 (docker-compose) ではなく v2 (docker compose) を使うように変数を設定
COMPOSE_COMMAND="docker compose"
COMPOSE_FILE="docker-compose.prod.yml"
NGINX_TEMPLATE="nginx/app.conf.template"
NGINX_CONF="nginx/conf.d/app.conf"
APP_SERVICE_NAME="app" # docker-compose.prod.yml 内のサービス名

# 必要なディレクトリを作成
echo ">>> 必要なディレクトリを作成しています..."
mkdir -p nginx/conf.d
mkdir -p certbot/conf
mkdir -p certbot/www

# すでに設定ファイルが存在する場合は処理をスキップ（初回起動のみ実行）
if [ -f "$NGINX_CONF" ]; then
  echo ">>> Nginx設定ファイル ($NGINX_CONF) が既に存在します。"
  # 既存のコンテナを起動する
  $COMPOSE_COMMAND -f $COMPOSE_FILE up -d
  echo ">>> 既存のコンテナを起動しました。"
  exit 0
fi

# 1. Certbotチャレンジ用のダミーNginx設定を作成
echo ">>> Certbotチャレンジ用のダミーNginx設定を作成しています..."
cat > "$NGINX_CONF" << EOF
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 404; # 証明書取得中は他をブロック
    }
}
EOF

# 2. Nginxを起動
echo ">>> Nginxを起動しています..."
$COMPOSE_COMMAND -f $COMPOSE_FILE up -d nginx

# 3. Certbotで証明書を取得
echo ">>> CertbotでSSL証明書を取得しています (Staging)..."
# まずはStaging環境でテスト（本番はレート制限があるため）
$COMPOSE_COMMAND -f $COMPOSE_FILE run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email $EMAIL \
  --domain $DOMAIN \
  --rsa-key-size 4096 \
  --agree-tos \
  --non-interactive \
  --staging

# Stagingが成功したら本番用を取得
if [ $? -eq 0 ]; then
  echo ">>> Staging成功。本番用証明書を取得します..."
  # Staging用の証明書を削除
  $COMPOSE_COMMAND -f $COMPOSE_FILE run --rm certbot delete --cert-name $DOMAIN
  
  # 本番用証明書を取得
  $COMPOSE_COMMAND -f $COMPOSE_FILE run --rm certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email $EMAIL \
    --domain $DOMAIN \
    --rsa-key-size 4096 \
    --agree-tos \
    --non-interactive
else
  echo ">>> Certbot (Staging) に失敗しました。ログを確認してください。"
  $COMPOSE_COMMAND -f $COMPOSE_FILE logs nginx
  $COMPOSE_COMMAND -f $COMPOSE_FILE logs certbot
  # ダミー設定を削除
  rm $NGINX_CONF
  exit 1
fi

if [ $? -ne 0 ]; then
  echo ">>> Certbot (本番) に失敗しました。ログを確認してください。"
  $COMPOSE_COMMAND -f $COMPOSE_FILE logs nginx
  $COMPOSE_COMMAND -f $COMPOSE_FILE logs certbot
  # ダミー設定を削除
  rm $NGINX_CONF
  exit 1
fi

echo ">>> SSL証明書の取得に成功しました。"

# 4. Nginxを停止
echo ">>> Nginxを一時停止しています..."
$COMPOSE_COMMAND -f $COMPOSE_FILE stop nginx

# 5. 本番用のNginx設定ファイル (app.conf) をテンプレートから作成
echo ">>> 本番用のNginx設定ファイルを作成しています..."
sed -e "s/{{DOMAIN}}/$DOMAIN/g" -e "s/{{APP_SERVICE_NAME}}/$APP_SERVICE_NAME/g" "$NGINX_TEMPLATE" > "$NGINX_CONF"

# 6. Diffie-Hellmanパラメータの生成 (初回のみ)
DHPARAM_FILE="certbot/conf/ssl-dhparams.pem"
if [ ! -f "$DHPARAM_FILE" ]; then
    echo ">>> Diffie-Hellman パラメータを生成しています (時間がかかります)..."
    $COMPOSE_COMMAND -f $COMPOSE_FILE run --rm certbot \
        openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048
fi

# 7. すべてのサービスを起動
echo ">>> すべてのサービスを起動しています..."
$COMPOSE_COMMAND -f $COMPOSE_FILE up -d --remove-orphans

# 8. Certbot自動更新の設定
# docker-compose.prod.yml の command で設定するか、
# ホストの cron で設定することを推奨します。
# (ホストのcron例)
# (crontab -l 2>/dev/null; echo "0 3,15 * * * /usr/bin/docker-compose -f /path/to/docker-compose.prod.yml run --rm certbot renew --quiet && /usr/bin/docker-compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload") | crontab -
echo ">>> セットアップ完了！"
echo ">>> Certbotの自動更新を設定してください (README参照)。"


