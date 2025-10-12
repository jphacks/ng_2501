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
        <div className="flex flex-col h-full min-w-0 w-full">
            {/* ヘッダー */}
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-gray-200">
                <h3 className="text-sm font-semibold text-gray-800">プロンプト確認・編集</h3>
            </div>

            {/* メインコンテンツ: 2カラムレイアウト（右は常に固定幅） */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-3 flex-1 min-h-0 min-w-0 w-full">
                {/* 左側: プロンプト編集エリア（メイン） */}
                <div className="flex flex-col min-h-0 min-w-0 w-full">
                    {/* プロンプト編集 */}
                    <div className="flex-1 min-h-0 flex flex-col overflow-auto w-full">{/* 左側は内部スクロール */}
                        <label
                            htmlFor="prompt-editor"
                            className="block text-xs font-medium text-gray-700 mb-1 flex-shrink-0"
                        >
                            動画生成プロンプト
                        </label>
                        <textarea
                            id="prompt-editor"
                            value={editedPrompt}
                            onChange={(e) => setEditedPrompt(e.target.value)}
                            className="w-full flex-1 p-3 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm resize-none"
                            disabled={isGenerating}
                        />
                        <p className="text-xs text-gray-500 mt-1 flex-shrink-0">
                            このプロンプトから動画が生成されます
                        </p>
                    </div>
                </div>

                {/* 右側: 操作エリア（固定幅・常に100%に見える） */}
                <div className="flex flex-col min-h-0 min-w-0 w-full lg:w-[420px]">
                    {/* スクロール可能エリア */}
                    <div className="overflow-y-auto flex-1 min-h-0 pr-1 space-y-2">{/* 右側も内部スクロール */}
                        {/* 原文表示 */}
                        <div className="bg-gray-50 border border-gray-200 rounded p-2">
                            <button
                                type="button"
                                onClick={() => setShowOriginal(!showOriginal)}
                                className="w-full flex items-center justify-between text-sm font-medium text-gray-700 hover:text-gray-900"
                            >
                                <span>動画の原文</span>
                                <svg
                                    className={`w-4 h-4 transition-transform ${showOriginal ? 'rotate-180' : ''}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <title>{showOriginal ? '閉じる' : '開く'}</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            {showOriginal && (
                                <div className="mt-2 pt-2 border-t border-gray-200">
                                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                                        {prompt.originalText}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Manimコード表示 */}
                        {prompt.manimCode && (
                            <div className="bg-gray-50 border border-gray-200 rounded p-2">
                                <button
                                    type="button"
                                    onClick={() => setShowManimCode(!showManimCode)}
                                    className="w-full flex items-center justify-between text-sm font-medium text-gray-700 hover:text-gray-900"
                                >
                                    <span>Manimコード</span>
                                    <svg
                                        className={`w-4 h-4 transition-transform ${showManimCode ? 'rotate-180' : ''}`}
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <title>{showManimCode ? '閉じる' : '開く'}</title>
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            {showManimCode && (
                                <div className="mt-2 pt-2 border-t border-gray-200">
                                    <textarea
                                        id="manim-code-editor"
                                        value={editedManimCode}
                                        onChange={(e) => setEditedManimCode(e.target.value)}
                                        className="w-full p-2 bg-gray-900 text-green-400 rounded border border-gray-700 h-48 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-xs overflow-x-auto resize-none"
                                        disabled={isGenerating}
                                        spellCheck={false}
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* 動画生成ボタン（固定位置） */}
                <div className="pt-2 border-t border-gray-200 mt-2">
                        <button
                            type="button"
                            onClick={handleGenerate}
                            disabled={!editedPrompt.trim() || isGenerating}
                            className="w-full bg-green-600 text-white py-3 px-4 rounded text-base font-semibold hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm flex items-center justify-center gap-2"
                        >
                            {isGenerating ? (
                                <>
                                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                        <title>生成中</title>
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    動画生成中...
                                </>
                            ) : (
                                <>
                                    動画を生成
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <title>生成</title>
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
