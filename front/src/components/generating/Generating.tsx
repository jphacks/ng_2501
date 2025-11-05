'use client'

/**
 * Presentation層: 動画生成中の表示コンポーネント
 */
export function Generating() {
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-200">
                <h3 className="text-lg font-bold text-gray-800">SUDO<span className="text-xs text-gray-500 ml-5">ー 生成中</span></h3>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
                <div className="flex justify-center mb-4">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">動画を生成中...</h3>
                <p className="text-sm text-gray-600">
                    数式動画を生成中です（約10〜20分）。しばらくお待ちください。
                </p>
            </div>
        </div>
    )
}
