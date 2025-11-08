#!/bin/bash

# Let's Encrypt 初期化スクリプト
# 初回のSSL証明書取得を行います

set -e

DOMAIN="ani-math.jp"
EMAIL="yumaboda.official@gmail.com"
STAGING=0  # テスト用証明書を使う場合は 1 に設定

echo "### Let's Encrypt の初期化を開始します ###"
echo "ドメイン: ${DOMAIN}"
echo "メールアドレス: ${EMAIL}"

# HTTP専用の設定ファイルをコピー
echo "### HTTP専用の設定ファイルを準備 ###"
cp ./nginx/conf.d/app-http-only.conf ./nginx/conf.d/app.conf.temp
mv ./nginx/conf.d/app.conf ./nginx/conf.d/app.conf.https.backup 2>/dev/null || true
mv ./nginx/conf.d/app.conf.temp ./nginx/conf.d/app.conf
echo "HTTP専用設定に切り替えました"

# すべてのサービスを起動（HTTP専用）
echo "### サービスを起動しています ###"
docker compose up -d
sleep 5
echo "サービスが起動しました"

# Recommended TLS parameters のダウンロード
echo "### TLSパラメータのダウンロード ###"
PARAMS_PATH="./certbot/conf/options-ssl-nginx.conf"
if [ ! -e "$PARAMS_PATH" ]; then
  echo "TLSパラメータをダウンロード中..."
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$PARAMS_PATH"
  echo "TLSパラメータをダウンロードしました"
fi

DHPARAMS_PATH="./certbot/conf/ssl-dhparams.pem"
if [ ! -e "$DHPARAMS_PATH" ]; then
  echo "DHパラメータをダウンロード中..."
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DHPARAMS_PATH"
  echo "DHパラメータをダウンロードしました"
fi

# 本番証明書の取得
echo "### Let's Encrypt証明書の取得 ###"
STAGING_ARG=""
if [ $STAGING != "0" ]; then
  STAGING_ARG="--staging"
  echo "ステージング環境で証明書を取得します（テスト用）"
fi

docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  $STAGING_ARG \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --force-renewal \
  -d "$DOMAIN"

# Nginxのリロード
echo "### Nginxをリロードしています ###"
docker compose exec nginx nginx -s reload

echo "### 完了しました！ ###"
echo "HTTPS が有効になりました: https://${DOMAIN}"
