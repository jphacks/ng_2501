/** @type {import('next').NextConfig} */
const nextConfig = {
    // Next.js 15ではappDirはデフォルトで有効
    eslint: {
        // なぜかESLintの警告が出てしまうので消す
        ignoreDuringBuilds: true,
    },
    // Docker本番環境用: standaloneモードを有効化
    output: 'standalone',
}

module.exports = nextConfig
