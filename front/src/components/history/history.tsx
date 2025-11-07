'use client'

import { useState, useEffect } from 'react'
import type { VideoInfo } from '@/app/datas/Video'
import { useDB } from '@/app/hooks/useDB'

interface HistoryProps {
    generationId: number
    onBack: () => void
}

/**
 * Presentation層: 動画履歴ページ
 */
export function History({ generationId, onBack }: HistoryProps) {
    const [videoHistory, setVideoHistory] = useState<VideoInfo[]>([])
    const { getAnimationHistory } = useDB()

    useEffect(() => {
        const fetchHistory = async () => {
            if (generationId) {
                const history = await getAnimationHistory(generationId)
                // sort by edit_count descending
                history.sort((a, b) => b.edit_count - a.edit_count)
                setVideoHistory(history)
            }
        }
        fetchHistory()
    }, [generationId, getAnimationHistory])

    return (
        <div className="flex flex-col h-full">
            {/* ヘッダー */}
            <div className="flex items-center mb-3 pb-3 border-b border-[#0A3B7E]/20">
                <button
                    type="button"
                    onClick={onBack}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-[#030405]/70 hover:text-[#030405] hover:bg-[#0A3B7E]/5 rounded transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <title>戻る</title>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    戻る
                </button>
                <div className="flex-1 text-center">
                    <span className="text-md text-[#030405]/50">ー 動画履歴 ー</span>
                </div>
                <h3 className="text-lg font-bold text-[#030405]">SUDO</h3>
            </div>

            {/* メインコンテンツ */}
            <div className="overflow-y-auto flex-1">
                <ul className="space-y-2">
                    {videoHistory.map((video) => (
                        <li key={video.video_id} className="flex items-center justify-between p-2 bg-white rounded shadow">
                            <span className="text-sm text-[#030405]/70">編集回数: {video.edit_count}</span>
                            <button
                                type="button"
                                onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '')}/api/animation/${video.video_id}`, '_blank')}
                                className="px-3 py-1 text-sm text-white bg-[#0A3B7E] rounded hover:bg-[#0A3B7E]/90"
                            >
                                動画を見る
                            </button>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    )
}

