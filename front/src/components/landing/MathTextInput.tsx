'use client'

import { useState } from 'react'

interface MathTextInputProps {
    onSubmit: (text: string, videoPrompt?: string) => Promise<void>
    isGenerating: boolean
}

/**
 * Presentation層: 数式テキスト入力フォーム
 */
export function MathTextInput({ onSubmit, isGenerating }: MathTextInputProps) {
    const [text, setText] = useState('')
    const [videoPrompt, setVideoPrompt] = useState('')
    const [showAdvanced, setShowAdvanced] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!text.trim()) return
        await onSubmit(text, videoPrompt || undefined)
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label htmlFor="math-text" className="block text-sm font-medium text-gray-700 mb-2">
                    数学テキスト
                </label>
                <textarea
                    id="math-text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="例: 積分の定義について説明します。∫f(x)dx は関数f(x)の原始関数を求める操作です。"
                    className="w-full p-4 border border-gray-300 rounded-lg h-40 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={isGenerating}
                />
            </div>

            {/* 詳細設定（トグル） */}
            <div>
                <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                    <span>{showAdvanced ? '▼' : '▶'}</span>
                    詳細設定（任意）
                </button>
                {showAdvanced && (
                    <div className="mt-3">
                        <label
                            htmlFor="video-prompt"
                            className="block text-sm font-medium text-gray-700 mb-2"
                        >
                            動画の追加プロンプト
                        </label>
                        <textarea
                            id="video-prompt"
                            value={videoPrompt}
                            onChange={(e) => setVideoPrompt(e.target.value)}
                            placeholder="例: 〇〇の数式を強調してほしい、〇〇の文字を青くしてほしい"
                            className="w-full p-4 border border-gray-300 rounded-lg h-24 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            disabled={isGenerating}
                        />
                    </div>
                )}
            </div>

            <button
                type="submit"
                disabled={!text.trim() || isGenerating}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
                {isGenerating ? 'プロンプト生成中...' : 'プロンプトを生成'}
            </button>
        </form>
    )
}
