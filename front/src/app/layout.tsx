import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Script from 'next/script'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Math Video Maker',
    description: 'Math video generator',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="ja">
            <head>
                <Script
                    src="https://unpkg.com/mathlive@0.107.1/dist/mathlive.min.js"
                    strategy="beforeInteractive"
                />
            </head>
            <body className={inter.className}>{children}</body>
        </html>
    )
}
