'use client'

import { useState } from 'react'
import { MathTextInput } from './MathTextInput'

interface LandingProps {
    onSubmit: (text: string, videoPrompt?: string) => Promise<void>
    isGenerating: boolean
    error: string | null
}

/**
 * Presentation層: ランディングページ全体
 */
export function Landing({ onSubmit, isGenerating, error }: LandingProps) {
    return (
        <div className="space-y-6">
            {/* エラー表示 */}
            {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-red-700 font-medium">エラー</p>
                    <p className="text-red-600 text-sm mt-1">{error}</p>
                </div>
            )}

            {/* テキスト入力フォーム */}
            <MathTextInput onSubmit={onSubmit} isGenerating={isGenerating} />
        </div>
    )
}
