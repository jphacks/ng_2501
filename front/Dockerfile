# フロントエンド用（Next.js）本番環境ビルド
FROM node:20-alpine AS base

# 依存関係をインストール
FROM base AS deps
WORKDIR /app

# package.jsonをコピー
COPY front/package*.json ./
RUN npm install

# アプリケーションをビルド
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY front/ .

# ビルド時の環境変数
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Next.jsのビルド
RUN npm run build

# 本番用イメージ
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

# 必要なファイルのみコピー
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
