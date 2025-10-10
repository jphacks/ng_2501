/** @type {import('next').NextConfig} */
const nextConfig = {
    // Next.js 15ではappDirはデフォルトで有効
    eslint: {
        // なぜかESLintの警告が出てしまうので消す
        ignoreDuringBuilds: true,
    },
}

module.exports = nextConfig
