'use client'

import { useState } from 'react'
import type { VideoInfo } from '@/app/datas/Video'
import { json } from 'stream/consumers'
import { useEffect } from 'react';
import { fetchScript } from '@/app/hooks/fetchScript';
import fetchVideo from '@/app/hooks/fetchVideo';

interface HistoryViewerProps {
    historyResult: VideoInfo[] | null
    onLoadVideo: (videoId: string, prompt: string) => Promise<any>
    onClose: () => void
}

/**
 * A component to display a single video card.
 * On hover, it shows the script.
 */
function HistoryCard({ video, onLoadVideo }: { video: VideoInfo; onLoadVideo: (videoId: string, prompt: string) => Promise<any> }) {
    const [isHovered, setIsHovered] = useState(false)
    const [content, setContent] = useState<string>('')
    const [script, setScript] = useState<string>('')
    const [editCount, setEditCount] = useState<number>(video.editCount)
    const [generateTime, setGenerateTime] = useState<string>(video.generateTime)
    const [isLoading, setIsLoading] = useState(true)
    const [manimCode, setManimCode] = useState<string>('')
    const [videoUrl, setVideoUrl] = useState<string>('')
    
    // フックはコンポーネントのトップレベルで呼び出す
    const { fetchScript: fetchScriptFn } = fetchScript();

    const handleVideoClick = async () => {
        try {
            console.log('Loading video:', video.videoId, 'with prompt:', content)
            await onLoadVideo(video.videoId, content)
        } catch (error) {
            console.error('Error loading video:', error)
        }
    }
    
    useEffect(() => {
        const fetchScriptContent = async () => {
            setIsLoading(true)
            try {
                // 動画URLを生成
                const url = await fetchVideo(video.videoId)
                if (url) {
                    setVideoUrl(url)
                }

                const scriptData = await fetchScriptFn(video.promptId)

                if (scriptData && scriptData.message) {
                    const message = typeof scriptData.message === 'string' ? JSON.parse(scriptData.message) : scriptData.message
                    if (message && Array.isArray(message.prompt)) {
                        const index = 3*(video.editCount - 1)
                        const item = message.prompt[index]

                        if (item && typeof item.content === 'string' && item.content!="") {
                            setContent(item.content)
                            setScript(item.content)
                        } else if (item && typeof item.enhance_prompt === 'string' && item.enhance_prompt!="") {
                            setContent(item.enhance_prompt)
                            setScript(item.enhance_prompt)
                        } else {
                            setContent('')
                            setScript('')
                        }
                    } else if (Array.isArray(message)) {
                        const index = 3*(video.editCount - 1)
                        if (message[index]['content'] === '' && message[index]['enhance_prompt']) {
                            setContent(message[index]['enhance_prompt'])
                            setScript('')
                        } else if (message[index]['content']) {
                            const content = message[index]['content']
                            const script = message[index+1]['content']
                            setContent(content)
                            setScript(script)
                        } else {
                            setContent('')
                            setScript('')
                        }
                    } else {
                        setContent('')
                        setScript('')
                    }
                }
            } catch (error) {
                console.error('Error fetching script content:', error);
            } finally {
                setIsLoading(false)
            }
        }
        fetchScriptContent();
        setEditCount(video.editCount);
        setGenerateTime(video.generateTime);
    }, [video.promptId, video.editCount, fetchScriptFn]);

    if (isLoading) {
        return <div className="w-full h-full flex items-center justify-center bg-gray-200 min-h-[200px]">
            <p className="text-gray-500">Loading...</p>
        </div>
    }

    return (
        <div className="relative group border rounded-lg shadow-lg bg-gray-200 hover:bg-gray-300"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            <div className="relative overflow-hidden rounded-t-lg">
                <button
                    type="button"
                    className="w-full h-full block"
                    onClick={handleVideoClick}
                >
                    <video
                        src={videoUrl}
                        className="w-full h-full object-cover"
                        playsInline
                        muted
                        autoPlay
                        loop
                        preload="auto"
                    />
                </button>
                {isHovered && (
                    <div 
                        className="absolute inset-x-0 top-0 bottom-0 bg-black bg-opacity-70 p-4 overflow-y-auto text-white animate-fade-in cursor-pointer"
                        onClick={handleVideoClick}
                    >
                        <h3 className="font-bold mb-2">Script</h3>
                        <p className="text-sm whitespace-pre-wrap">{content || 'No script available'}</p>
                    </div>
                )}
            </div>
            <div 
                className={`bg-white rounded-b-lg transition-all duration-300 ease-in-out overflow-hidden ${
                    isHovered ? 'max-h-48 p-2 opacity-100' : 'max-h-0 p-0 opacity-0'
                }`}
            >
                <p className="text-xs text-gray-600">Edited {editCount} times</p>
                <p className="text-xs text-gray-600">Generated on {new Date(generateTime).toLocaleString()}</p>
                <p className="mt-1 font-semibold text-gray-800">Prompt:</p>
                <div className="mt-2 max-h-32 overflow-y-auto border-t-2 pb-4">
                    <p className="text-sm font-medium text-gray-800 whitespace-pre-wrap">{script}</p>
                </div>
            </div>
        </div>
    )
    
}

/**
 * Presentation層: 検索された動画をグリッド表示する
 * Youtubeのホーム画面のように、動画が並びカーソルを合わせるとスクリプトが表示される
 */
export function HistoryViewer({ historyResult, onLoadVideo, onClose }: HistoryViewerProps) {
    if (!historyResult || historyResult.length === 0) {
        return (
            <div className="text-center">
                <p className="text-gray-500">No videos found.</p>
                <button onClick={onClose} className="mt-4 px-4 py-2 text-sm font-medium text-white bg-[#0A3B7E] rounded hover:bg-[#0A3B7E]/90">
                    Back to Home
                </button>
            </div>
        )
    }
    console.log('Rendering historyResult:', historyResult);

    return (
        <div>
            <div className="p-4">
                <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-white bg-[#0A3B7E] rounded hover:bg-[#0A3B7E]/90">
                    Back to Home
                </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4">
                {historyResult.map((video) => (
                    <HistoryCard key={video.videoId} video={video} onLoadVideo={onLoadVideo} />
                ))}
            </div>
        </div>
    )
}
