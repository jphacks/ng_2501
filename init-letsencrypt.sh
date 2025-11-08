#!/bin/bash

# Let's Encrypt 初期化スクリプト
# 初回のSSL証明書取得を行います

set -e

DOMAIN="ani-math.jp"
EMAIL="admin@${DOMAIN}"  # 管理者のメールアドレスを適切に設定してください
STAGING=0  # テスト用証明書を使う場合は 1 に設定

echo "### Let's Encrypt の初期化を開始します ###"
echo "ドメイン: ${DOMAIN}"
echo "メールアドレス: ${EMAIL}"

# ダミー証明書ディレクトリの作成
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}"
echo "### ダミー証明書の作成 ###"

mkdir -p "./certbot/conf/live/${DOMAIN}"
if [ ! -e "./certbot/conf/live/${DOMAIN}/privkey.pem" ]; then
  echo "ダミー証明書を生成中..."
  docker compose run --rm --entrypoint "\
    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
      -keyout '/etc/letsencrypt/live/${DOMAIN}/privkey.pem' \
      -out '/etc/letsencrypt/live/${DOMAIN}/fullchain.pem' \
      -subj '/CN=localhost'" certbot
  echo "ダミー証明書を作成しました"
else
  echo "ダミー証明書は既に存在します"
fi

# Nginxの起動
echo "### Nginxを起動しています ###"
docker compose up -d nginx

# ダミー証明書の削除
echo "### ダミー証明書を削除しています ###"
docker compose run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/${DOMAIN} && \
  rm -rf /etc/letsencrypt/archive/${DOMAIN} && \
  rm -rf /etc/letsencrypt/renewal/${DOMAIN}.conf" certbot
echo "ダミー証明書を削除しました"

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
