'use client'

import Image from 'next/image'

interface HeaderProps {
    /** 画面の状態を示すテキスト（例: "生成中", "動画結果"） */
    statusText?: string
    /** 戻るボタンを表示するか */
    showBackButton?: boolean
    /** 戻るボタンクリック時のハンドラー */
    onBack?: () => void
    /** 左側にカスタムコンテンツを表示（戻るボタンの代わり） */
    leftContent?: React.ReactNode
}

/**
 * 共通ヘッダーコンポーネント
 * 左: 戻るボタン（オプション）
 * 中央: ステータステキスト
 * 右: SUDOロゴ
 */
export function Header({ statusText, showBackButton = false, onBack, leftContent }: HeaderProps) {
    return (
        <div className="flex items-center mb-3 pb-3 border-b border-[#0A3B7E]/20">
            {/* 左: カスタムコンテンツ or 戻るボタン */}
            <div className="flex-1">
                {leftContent ? (
                    leftContent
                ) : showBackButton && onBack ? (
                    <button
                        type="button"
                        onClick={onBack}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#030405]/70 hover:text-[#030405] hover:bg-[#0A3B7E]/5 rounded transition-colors"
                    >
                        <div className="hidden min-[426px]:block">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <title>戻る</title>
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                        </div>
                        戻る
                    </button>
                ) : null}
            </div>

            {/* 中央: ステータステキスト */}
            <div className="flex-1 text-center px-1">
                {statusText && (
                    <span className="text-xs sm:text-sm md:text-base text-[#030405]/50 whitespace-nowrap">ー {statusText} ー</span>
                )}
            </div>

            {/* 右: SUDOロゴ */}
            <div className="flex-1 flex justify-end">
                <Image
                    src="/sudo-header-logo.png"
                    alt="SUDO"
                    width={80}
                    height={32}
                    className="h-6 sm:h-7 md:h-8 w-auto"
                    priority
                />
            </div>
        </div>
    )
}

