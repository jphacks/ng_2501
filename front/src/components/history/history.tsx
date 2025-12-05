'use client'

import { HistoryViewer } from './historyViewer'
import type { VideoInfo } from '@/app/datas/Video'

interface HistoryProps {
    historyResult: VideoInfo[] | null
    onLoadVideo: (videoId: string, prompt: string) => Promise<any>
    onClose: () => void
}

/**
 * Presentation層: 検索結果ページ全体
 */
export function History({ historyResult, onLoadVideo, onClose }: HistoryProps) {
    return (
        <div className="h-full flex flex-col min-w-0 w-full">
            <HistoryViewer historyResult={historyResult} onLoadVideo={onLoadVideo} onClose={onClose} />
        </div>
    )
}
