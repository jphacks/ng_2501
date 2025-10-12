'use client'

import { useState } from 'react'
import type { VideoResult } from '../../app/datas/Video'
import { VideoPlayer } from './VideoPlayer'

interface ResultProps {
    result: VideoResult
    isGenerating: boolean
    onEdit: (videoId: string, editPrompt: string) => Promise<VideoResult>
    onReset?: () => void
}

/**
 * Presentation層: リザルトページ全体
 * PC向けに画面を贅沢に使う2カラムレイアウト
 */
export function Result({ result, isGenerating, onEdit, onReset }: ResultProps) {
    const [showEditPanel, setShowEditPanel] = useState(false)
    const [editPrompt, setEditPrompt] = useState('')

    const handleEdit = async () => {
        if (!editPrompt.trim()) return
        await onEdit(result.videoId, editPrompt)
        setEditPrompt('')
        setShowEditPanel(false)
    }

    return (
        <div className="flex flex-col h-full">
            {/* ヘッダー */}
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-gray-800">動画生成完了</h2>
                {onReset && (
                    <button
                        type="button"
                        onClick={onReset}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <title>最初に戻る</title>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        最初に戻る
                    </button>
                )}
            </div>

            {/* メインコンテンツ: 2カラムレイアウト */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 min-h-0 min-w-0">
                {/* 左側: 動画プレイヤー（メイン） */}
                <div className="lg:col-span-2 flex flex-col min-h-0 min-w-0 w-full">
                    <VideoPlayer videoUrl={result.videoUrl} />
                </div>

                {/* 右側: 編集エリア */}
                <div className="flex flex-col min-h-0 min-w-0 w-full">
                    {/* 編集パネル切り替えボタン */}
                    <button
                        type="button"
                        onClick={() => setShowEditPanel(!showEditPanel)}
                        disabled={isGenerating}
                        className={`w-full py-3 px-4 rounded font-medium transition-all mb-3 ${
                            showEditPanel 
                                ? 'bg-gray-600 text-white hover:bg-gray-700' 
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                        } disabled:bg-gray-400 disabled:cursor-not-allowed`}
                    >
                        {showEditPanel ? '編集をキャンセル' : '動画を編集する'}
                    </button>

                    {/* 編集パネル */}
                    {showEditPanel && (
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded space-y-3 animate-fade-in mb-3">
                                <div>
                                    <label htmlFor="edit-prompt" className="block text-sm font-medium text-gray-700 mb-2">
                                        修正指示
                                    </label>
                                    <textarea
                                        id="edit-prompt"
                                        value={editPrompt}
                                        onChange={(e) => setEditPrompt(e.target.value)}
                                        placeholder="例: 図と式が重なっているので、図を左にずらしてください"
                                        className="w-full p-3 border border-gray-300 rounded text-sm h-32 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                        disabled={isGenerating}
                                    />
                                </div>

                                <button
                                    type="button"
                                    onClick={handleEdit}
                                    disabled={!editPrompt.trim() || isGenerating}
                                    className="w-full bg-blue-600 text-white py-2.5 px-4 rounded font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                                >
                                    {isGenerating ? (
                                        <span className="flex items-center justify-center gap-2">
                                            <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <title>読み込み中</title>
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                            </svg>
                                            再生成中...
                                        </span>
                                    ) : (
                                        '動画を再生成'
                                    )}
                                </button>
                        </div>
                    )}

                    {/* 使用されたプロンプト */}
                    <div className="flex flex-col border border-gray-200 rounded bg-white flex-1 min-h-0">
                        <div className="p-3 bg-gray-50 border-b border-gray-200">
                            <h4 className="text-sm font-medium text-gray-700">使用されたプロンプト</h4>
                        </div>
                        <div className="p-3 overflow-y-auto flex-1">
                            <p className="text-sm text-gray-700 whitespace-pre-wrap">
                                {result.prompt.prompt}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
