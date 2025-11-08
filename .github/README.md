# GCE + Nginx + Let's Encrypt + CI/CD セットアップガイド


これは、Google Compute Engine (GCE) 上で Docker Compose を使用し、NginxによるHTTPSリバースプロキシとLet's EncryptによるSSL証明書の自動更新、GitHub ActionsによるCI/CDを実現するためのガイド


## GCEインスタンスへのソフトウェアインストール

- Dockerのインストール 
- gitのインストトール


```
curl https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl start docker
sudo systemctl enable docker
sudo curl -L https://github.com/docker/compose/releases/download/1.16.1/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

gitからクローンして必要なファイルを取得
ロジェクトルート（/workspaces/ai_agent）から実行
```
chmod +x .devcontainer/init-letsencrypt.sh
# ドメイン名とメールアドレスを指定して実行
sudo DOMAIN=ani-math.jp EMAIL=yumaboda.official@gmail.com .devcontainer/init-letsencrypt.sh
```