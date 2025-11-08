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
COMPOSE_FILE="docker-compose.yml" # ユーザーの指定に合わせて .prod を削除
NGINX_TEMPLATE="nginx/app.conf.template"
NGINX_CONF="nginx/conf.d/app.conf"
APP_SERVICE_NAME="app" # docker-compose.yml 内のサービス名

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
  --d $DOMAIN \
  --rsa-key-size 4096 \
  --agree-tos \
  --non-interactive \
  --staging

# Stagingが成功したら本番用を取得
if [ $? -eq 0 ]; then
  echo ">>> Staging成功。本番用証明書を取得します..."
  # Staging用の証明書を削除 (古い証明書が残っている場合を考慮)
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
  sudo rm $NGINX_CONF
  exit 1
fi

if [ $? -ne 0 ]; then
  echo ">>> Certbot (本番) に失敗しました。ログを確認してください。"
  $COMPOSE_COMMAND -f $COMPOSE_FILE logs nginx
  $COMPOSE_COMMAND -f $COMPOSE_FILE logs certbot
  # ダミー設定を削除
  sudo rm $NGINX_CONF
  exit 1
fi

echo ">>> SSL証明書の取得に成功しました。"

# 4. Nginxを停止
echo ">>> Nginxを一時停止しています..."
$COMPOSE_COMMAND -f $COMPOSE_FILE stop nginx

# 5. 本番用のNginx設定ファイル (app.conf) をテンプレートから作成
echo ">>> 本番用のNginx設定ファイルを作成しています..."
sed -e "s/{{DOMAIN}}/$DOMAIN/g" -e "s/{{APP_SERVICE_NAME}}/$APP_SERVICE_NAME/g" "$NGINX_TEMPLATE" > "$NGINX_CONF"

# 6. 不足しているSSL設定ファイル (options-ssl-nginx.conf) をダウンロード
# (デバッグで判明したNginx起動エラーの修正)
SSL_OPTIONS_FILE="certbot/conf/options-ssl-nginx.conf"
if [ ! -f "$SSL_OPTIONS_FILE" ]; then
    echo ">>> Nginx用SSL推奨設定 (options-ssl-nginx.conf) をダウンロードしています..."
    # certbotコンテナ内の /etc/letsencrypt に保存する
    $COMPOSE_COMMAND -f $COMPOSE_FILE run --rm --entrypoint="wget" certbot -q https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf -O /etc/letsencrypt/options-ssl-nginx.conf
fi

# 7. Diffie-Hellmanパラメータの生成 (初回のみ)
# (デバッグで判明したコマンドのバグを修正)
DHPARAM_FILE="certbot/conf/ssl-dhparams.pem"
if [ ! -f "$DHPARAM_FILE" ]; then
    echo ">>> Diffie-Hellman パラメータを生成しています (時間がかかります)..."
    # certbotコンテナの中で openssl を実行し、/etc/letsencrypt に保存する
    $COMPOSE_COMMAND -f $COMPOSE_FILE run --rm --entrypoint="openssl" certbot dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048
fi

# 8. すべてのサービスを起動
echo ">>> すべてのサービスを起動しています..."
$COMPOSE_COMMAND -f $COMPOSE_FILE up -d --remove-orphans

# 9. Certbot自動更新の設定 (ホストのcronを使用)
echo ">>> Certbot自動更新用のCronジョブを設定しています..."
# GCEインスタンス上の絶対パスを取得 (APP_DIR変数がないため、カレントディレクトリから推定)
APP_DIR=$(pwd)
# cron実行ユーザー ($USER) が docker グループに属している必要がある
CRON_COMMAND="0 3,15 * * * $COMPOSE_COMMAND -f $APP_DIR/$COMPOSE_FILE run --rm certbot renew --quiet && $COMPOSE_COMMAND -f $APP_DIR/$COMPOSE_FILE exec nginx nginx -s reload"
# 既存のcrontabを保持しつつ、重複を避けて追加
(crontab -l 2>/dev/null | grep -v -F "certbot renew" ; echo "$CRON_COMMAND") | crontab -

echo ">>> セットアップ完了！"
echo ">>> GCEホストのcrontabに自動更新ジョブを追加しました。"