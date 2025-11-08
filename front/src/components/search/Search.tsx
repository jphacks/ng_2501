'use client'

import { VideoViewer } from './VideoViewer'
import type { VideoData } from '@/app/datas/Video'

interface SearchProps {
    result: VideoData[]
    isGenerating: boolean
    onLoadVideo: (videoId: string, prompt: string) => Promise<any>
    onReset?: () => void
}

/**
 * Presentation層: 検索結果ページ全体
 */
export function Search({ result, isGenerating, onLoadVideo, onReset }: SearchProps) {
    return (
        <div className="h-full flex flex-col min-w-0 w-full">
            <VideoViewer result={result} isGenerating={isGenerating} onLoadVideo={onLoadVideo} onReset={onReset} />
        </div>
    )
}
