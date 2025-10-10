'use client'

import { useState } from 'react'
import type { VideoGenerationPrompt, VideoResult } from '../../app/datas/Video'

interface PromptEditorProps {
    prompt: VideoGenerationPrompt
    isGenerating: boolean
    onGenerate: (prompt: VideoGenerationPrompt) => Promise<VideoResult>
}

/**
 * Presentation層: プロンプト編集コンポーネント
 */
export function PromptEditor({ prompt, isGenerating, onGenerate }: PromptEditorProps) {
    const [editedPrompt, setEditedPrompt] = useState(prompt.prompt)
    const [editedManimCode, setEditedManimCode] = useState(prompt.manimCode || '')
    const [showOriginal, setShowOriginal] = useState(false)
    const [showManimCode, setShowManimCode] = useState(false)

    const handleGenerate = () => {
        onGenerate({
            ...prompt,
            prompt: editedPrompt,
            manimCode: editedManimCode || undefined,
        })
    }

    return (
        <div className="space-y-4">
            {/* プロンプト編集エリア */}
            <div>
                <div className="flex justify-between items-center mb-2">
                    <label
                        htmlFor="prompt-editor"
                        className="block text-sm font-medium text-gray-700"
                    >
                        動画生成プロンプト
                    </label>
                    <button
                        type="button"
                        onClick={() => setShowOriginal(!showOriginal)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                    >
                        {showOriginal ? '原文を隠す' : '原文を表示'}
                    </button>
                </div>

                {showOriginal && (
                    <div className="mb-3 p-3 bg-gray-100 rounded-lg border border-gray-300">
                        <p className="text-sm text-gray-700 font-medium mb-1">原文:</p>
                        <p className="text-sm text-gray-600 whitespace-pre-wrap">
                            {prompt.originalText}
                        </p>
                    </div>
                )}

                <textarea
                    id="prompt-editor"
                    value={editedPrompt}
                    onChange={(e) => setEditedPrompt(e.target.value)}
                    className="w-full p-4 border border-gray-300 rounded-lg h-32 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    disabled={isGenerating}
                />
            </div>

            {/* Manimコード編集エリア（トグル） */}
            {prompt.manimCode && (
                <div>
                    <button
                        type="button"
                        onClick={() => setShowManimCode(!showManimCode)}
                        className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                        <span>{showManimCode ? '▼' : '▶'}</span>
                        Manimコードを{showManimCode ? '隠す' : '編集'}
                    </button>
                    {showManimCode && (
                        <div className="mt-3">
                            <label
                                htmlFor="manim-code-editor"
                                className="block text-sm font-medium text-gray-700 mb-2"
                            >
                                Manimコード（編集可能）
                            </label>
                            <textarea
                                id="manim-code-editor"
                                value={editedManimCode}
                                onChange={(e) => setEditedManimCode(e.target.value)}
                                className="w-full p-4 bg-gray-900 text-green-400 rounded-lg border border-gray-700 h-64 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-xs overflow-x-auto"
                                disabled={isGenerating}
                                spellCheck={false}
                            />
                        </div>
                    )}
                </div>
            )}

            {/* 生成ボタン */}
            <button
                type="button"
                onClick={handleGenerate}
                disabled={!editedPrompt.trim() || isGenerating}
                className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
                {isGenerating ? '動画生成中...' : '動画を生成'}
            </button>
        </div>
    )
}
