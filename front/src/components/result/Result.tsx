'use client'

import { useState } from 'react'
import type { VideoResult } from '../../app/datas/Video'
import { VideoEditDialog } from './VideoEditDialog'
import { VideoPlayer } from './VideoPlayer'

interface ResultProps {
    result: VideoResult
    isGenerating: boolean
    onEdit: (videoId: string, editPrompt: string) => Promise<VideoResult>
}

/**
 * Presentation層: リザルトページ全体
 */
export function Result({ result, isGenerating, onEdit }: ResultProps) {
    const [showEditDialog, setShowEditDialog] = useState(false)

    const handleEdit = async (editPrompt: string) => {
        await onEdit(result.videoUrl, editPrompt)
        setShowEditDialog(false)
    }

    return (
        <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">
                    ステップ3: 動画が生成されました
                </h3>
            </div>

            {/* 動画プレイヤー */}
            <VideoPlayer videoUrl={result.videoUrl} />

            {/* 使用されたプロンプト */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">使用されたプロンプト:</h4>
                <p className="text-sm text-gray-600 whitespace-pre-wrap">{result.prompt.prompt}</p>
            </div>

            {/* 動画編集ダイアログ */}
            <VideoEditDialog
                isOpen={showEditDialog}
                isGenerating={isGenerating}
                onClose={() => setShowEditDialog(false)}
                onEdit={handleEdit}
                onOpenDialog={() => setShowEditDialog(true)}
            />
        </div>
    )
}
