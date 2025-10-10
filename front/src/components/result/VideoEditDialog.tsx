'use client'

import { useState } from 'react'

interface VideoEditDialogProps {
    isOpen: boolean
    isGenerating: boolean
    onClose: () => void
    onEdit: (editPrompt: string) => Promise<void>
    onOpenDialog: () => void
}

/**
 * Presentation層: 動画編集ダイアログコンポーネント
 */
export function VideoEditDialog({
    isOpen,
    isGenerating,
    onClose,
    onEdit,
    onOpenDialog,
}: VideoEditDialogProps) {
    const [editPrompt, setEditPrompt] = useState('')

    const handleEdit = async () => {
        if (!editPrompt.trim()) return
        await onEdit(editPrompt)
        setEditPrompt('')
    }

    return (
        <>
            {/* 動画編集ボタン */}
            <button
                type="button"
                onClick={onOpenDialog}
                disabled={isGenerating}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
                動画を編集する
            </button>

            {/* 編集ダイアログ */}
            {isOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <h3 className="text-xl font-bold text-gray-800 mb-4">動画を編集</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            動画の不具合や改善点を説明してください
                        </p>

                        <textarea
                            value={editPrompt}
                            onChange={(e) => setEditPrompt(e.target.value)}
                            placeholder="例: 図と式が重なっているので修正してほしい"
                            className="w-full p-4 border border-gray-300 rounded-lg h-32 focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-4"
                            disabled={isGenerating}
                        />

                        <div className="flex gap-3">
                            <button
                                type="button"
                                onClick={handleEdit}
                                disabled={!editPrompt.trim() || isGenerating}
                                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                            >
                                {isGenerating ? '再生成中...' : '再生成'}
                            </button>
                            <button
                                type="button"
                                onClick={onClose}
                                disabled={isGenerating}
                                className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-400 disabled:bg-gray-200 disabled:cursor-not-allowed transition-colors"
                            >
                                キャンセル
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
