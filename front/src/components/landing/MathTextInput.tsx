'use client'

import { useState } from 'react'
import { MathEditor } from '@/components/math/MathEditor'
import { ErrorProvider } from '@/app/contexts/ErrorContext'

interface MathTextInputProps {
    onSubmit: (text: string, videoPrompt?: string) => Promise<void>
    isGenerating: boolean
}

/**
 * Presentation層: 数式テキスト入力フォーム（MathEditor統合版）
 */
export function MathTextInput({ onSubmit, isGenerating }: MathTextInputProps) {
    const [text, setText] = useState('')
    const [videoPrompt, setVideoPrompt] = useState('')
    const [showAdvanced, setShowAdvanced] = useState(false)
    const [showMathEditor, setShowMathEditor] = useState(false)
    const [currentMathValue, setCurrentMathValue] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!text.trim()) return
        await onSubmit(text, videoPrompt || undefined)
    }

    const handleMathEditorOpen = () => {
        setCurrentMathValue('')
        setShowMathEditor(true)
    }

    const handleMathComplete = (latex: string) => {
        // Insert the LaTeX formula into the text at cursor position
        // For now, we'll just append it with proper delimiters
        const mathFormula = `$${latex}$`
        setText((prev) => {
            if (prev.trim()) {
                return `${prev} ${mathFormula}`
            }
            return mathFormula
        })
        setShowMathEditor(false)
        setCurrentMathValue('')
    }

    const handleMathCancel = () => {
        setShowMathEditor(false)
        setCurrentMathValue('')
    }

    return (
        <ErrorProvider>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <label htmlFor="math-text" className="block text-sm font-medium text-gray-700">
                            数学テキスト
                        </label>
                        <button
                            type="button"
                            onClick={handleMathEditorOpen}
                            disabled={isGenerating}
                            className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:text-gray-400"
                        >
                            ＋ 数式を入力
                        </button>
                    </div>
                    <textarea
                        id="math-text"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="例: 積分の定義について説明します。∫f(x)dx は関数f(x)の原始関数を求める操作です。数式を追加するには「数式を入力」ボタンをクリックしてください。"
                        className="w-full p-4 border border-gray-300 rounded-lg h-40 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={isGenerating}
                    />
                </div>

                {/* 数式エディタ */}
                {showMathEditor && (
                    <div className="p-4 border border-blue-300 rounded-lg bg-blue-50">
                        <h3 className="text-sm font-medium text-gray-700 mb-3">数式エディタ</h3>
                        <MathEditor
                            value={currentMathValue}
                            onChange={setCurrentMathValue}
                            onComplete={() => handleMathComplete(currentMathValue)}
                            onCancel={handleMathCancel}
                            isVisible={true}
                        />
                        <p className="mt-2 text-xs text-gray-600">
                            Enterキーで確定、Escキーでキャンセルできます
                        </p>
                    </div>
                )}

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
        </ErrorProvider>
    )
}
