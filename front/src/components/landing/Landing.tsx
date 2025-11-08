'use client'

import { MathTextInput } from './MathTextInput'
import { SearchBar } from '../search/SearchBar'

interface LandingProps {
    onSubmit: (text: string, videoPrompt?: string) => Promise<void>
    onSearch: (query: string) => void
    isGenerating: boolean
    error: string | null
    children?: React.ReactNode // テスト用コンポーネント挿入用
}

/**
 * Presentation層: ランディングページ全体
 */
export function Landing({ onSubmit, onSearch, isGenerating, error, children }: LandingProps) {
    return (
        <div className="flex flex-col h-full min-w-0">
            {/* エラー表示 */}
            {error && (
                <div className="p-3 bg-red-50 border border-red-300 rounded mb-3">
                    <p className="text-sm font-medium text-red-800">エラーが発生しました</p>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
            )}

            {/* 検索バー */}
            <SearchBar onSearch={onSearch} isGenerating={isGenerating} />

            {/* テスト用コンポーネント挿入スロット */}
            {children}

            {/* テキスト入力フォーム（flex-1で残りスペース占有） */}
            <div className="flex-1 min-h-0 overflow-hidden">
                <MathTextInput onSubmit={onSubmit} isGenerating={isGenerating} />
            </div>
        </div>
    )
}
