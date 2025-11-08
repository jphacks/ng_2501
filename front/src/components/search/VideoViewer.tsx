'use client'

import { useState } from 'react'
import type { VideoData } from '@/app/datas/Video'

interface VideoViewerProps {
    result: VideoData[]
    isGenerating: boolean
    onLoadVideo: (videoId: string, prompt: string) => Promise<any>
    onReset?: () => void
}

/**
 * A component to display a single video card.
 * On hover, it shows the script.
 */
function VideoCard({ video, onLoadVideo }: { video: VideoData; onLoadVideo: (videoId: string, prompt: string) => Promise<any> }) {
    const [isHovered, setIsHovered] = useState(false)

    return (
        <div className="relative group border rounded-lg overflow-hidden shadow-lg bg-gray-200 hover:bg-gray-300"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <button
                type="button"
                className="w-full h-full"
                onClick={() => onLoadVideo(video.videoId, video.content)}
            >
                <video
                    src={video.videoPath}
                    className="w-full h-full object-cover"
                    playsInline
                    muted
                    loop={isHovered}
                    autoPlay={isHovered}
                    preload="metadata"
                />
                {isHovered && (
                    <div className="absolute inset-0 bg-black bg-opacity-70 p-4 overflow-y-auto text-white animate-fade-in">
                        <h3 className="font-bold mb-2">Script</h3>
                        <p className="text-sm whitespace-pre-wrap">{video.content}</p>
                    </div>
                )}
            </button>
        </div>
    )
}

/**
 * Presentation層: 検索された動画をグリッド表示する
 * Youtubeのホーム画面のように、動画が並びカーソルを合わせるとスクリプトが表示される
 */
export function VideoViewer({ result, isGenerating, onLoadVideo, onReset }: VideoViewerProps) {
    if (!result || result.length === 0) {
        return (
            <div className="text-center">
                <p className="text-gray-500">No videos found.</p>
                <button onClick={onReset} className="mt-4 px-4 py-2 text-sm font-medium text-white bg-[#0A3B7E] rounded hover:bg-[#0A3B7E]/90">
                    Back to Home
                </button>
            </div>
        )
    }

    return (
        <div>
            <div className="p-4">
                <button onClick={onReset} className="px-4 py-2 text-sm font-medium text-white bg-[#0A3B7E] rounded hover:bg-[#0A3B7E]/90">
                    Back to Home
                </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4">
                {result.map((video) => (
                    <VideoCard key={video.videoId} video={video} onLoadVideo={onLoadVideo} />
                ))}
            </div>
        </div>
    )
}
