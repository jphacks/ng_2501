'use client'

import { Header } from '../common/Header'

/**
 * Presentation層: 動画生成中の表示コンポーネント
 */
export function Generating() {
    return (
        <div className="space-y-4">
            <Header statusText="生成中" />
            <div className="bg-[#0A3B7E]/5 border border-[#0A3B7E]/20 rounded-lg p-8 text-center">
                <div className="flex justify-center mb-4">
                    <img 
                        src="/sudo-generating.gif" 
                        alt="生成中" 
                        className="w-48 h-48 object-contain"
                    />
                </div>
                <h3 className="text-lg font-semibold text-[#030405] mb-2">動画を生成中...</h3>
                <p className="text-sm text-[#030405]/70">
                    数式動画を生成中です（約10〜20分）。しばらくお待ちください。
                </p>
            </div>
        </div>
    )
}
