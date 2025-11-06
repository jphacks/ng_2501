'use client'

/**
 * Presentation層: 動画生成中の表示コンポーネント
 */
export function Generating() {
    return (
        <div className="space-y-4">
            <div className="flex items-center mb-3 pb-3 border-b border-[#0A3B7E]/20">
                <div className="flex-1"></div>
                <div className="flex-1 text-center">
                    <span className="text-md text-[#030405]/50">ー 生成中 ー</span>
                </div>
                <div className="flex-1 text-right">
                    <h3 className="text-lg font-bold text-[#030405]">SUDO</h3>
                </div>
            </div>
            <div className="bg-[#0A3B7E]/5 border border-[#0A3B7E]/20 rounded-lg p-8 text-center">
                <div className="flex justify-center mb-4">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[#3A947C]" />
                </div>
                <h3 className="text-lg font-semibold text-[#030405] mb-2">動画を生成中...</h3>
                <p className="text-sm text-[#030405]/70">
                    数式動画を生成中です（約10〜20分）。しばらくお待ちください。
                </p>
            </div>
        </div>
    )
}
