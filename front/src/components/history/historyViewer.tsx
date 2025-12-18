'use client'

import { useState } from 'react';
import type { VideoInfo } from '@/app/datas/Video';
import { useEffect } from 'react';
import { fetchScript } from '@/app/hooks/fetchScript';
import { fetchManimCode } from '@/app/hooks/fetchManimCode';
import fetchVideo from '@/app/hooks/fetchVideo';
import { Header } from '../common/Header';

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
    const [title, setTitle] = useState<string>('Script')
    const [script, setScript] = useState<string>('')
    const [editCount, setEditCount] = useState<number>(video.editCount)
    const [generateTime, setGenerateTime] = useState<string>(video.generateTime)
    const [isLoading, setIsLoading] = useState(true)
    const [manimCode, setManimCode] = useState<string>('')
    const [videoUrl, setVideoUrl] = useState<string>('')
    
    // フックはコンポーネントのトップレベルで呼び出す
    const { fetchScript: fetchScriptFn } = fetchScript();
    const { fetchManimCode: fetchManimCodeFn } = fetchManimCode();

    const handleVideoClick = async () => {
        try {
            console.log('Loading video:', video.videoId, 'with prompt:', content)
            await onLoadVideo(video.videoId, content)
        } catch (error) {
            console.error('Error loading video:', error)
        }
    }
    
    useEffect(() => {
        const fetchAllContent = async () => {
            setIsLoading(true)
            try {
                // 動画URLを生成
                console.log('Fetching video URL for:', video.videoId)
                const url = await fetchVideo(video.videoId)
                if (url) {
                    setVideoUrl(url)
                    console.log('Video URL fetched:', url)
                }

                // スクリプトを取得
                console.log('Fetching script for promptId:', video.promptId)
                const scriptData = await fetchScriptFn(video.promptId)
                console.log('Script data received:', scriptData)

                if (scriptData && scriptData.message) {
                    const message = typeof scriptData.message === 'string' ? JSON.parse(scriptData.message) : scriptData.message
                    if (message && Array.isArray(message.prompt)) {
                        const index = 3*(video.editCount - 1)
                        const item = message.prompt[index]

                        if (item && typeof item.content === 'string' && item.content!="") {
                            setContent(item.content)
                            setScript(item.content)
                            setTitle('Script')
                        } else if (item && typeof item.enhance_prompt === 'string' && item.enhance_prompt!="") {
                            setContent(item.enhance_prompt)
                            setScript(item.enhance_prompt)
                            setTitle('Script')
                        } else {
                            setContent('')
                            setScript('')
                            setTitle('Script')
                        }
                    } else if (Array.isArray(message)) {
                        const index = 3*(video.editCount - 1)
                        if (message[index]['content'] === '' && message[index]['enhance_prompt']) {
                            setContent(message[index]['enhance_prompt'])
                            setScript('')
                            setTitle('Enhance Script')
                        } else if (message[index]['content']) {
                            const content = message[index]['content']
                            const script = message[index+1]['content']
                            setContent(content)
                            setScript(script)
                            setTitle('Script')
                        } else {
                            setContent('')
                            setScript('')
                            setTitle('Script')
                        }
                    } else {
                        setContent('')
                        setScript('')
                        setTitle('Script')
                    }
                }

                // Manimコードを取得
                console.log('Fetching manim code for manimCodeId:', video.manimCodeId)
                const manimCodeData = await fetchManimCodeFn(video.manimCodeId)
                console.log('Manim code data received:', manimCodeData)
                
                if (manimCodeData && manimCodeData.message) {
                    setManimCode(manimCodeData.message)
                } else {
                    setManimCode('')
                }
            } catch (error) {
                if (error instanceof Error) {
                    console.error('Error details:', error.message, error.stack)
                }
            } finally {
                setIsLoading(false)
            }
        }
        
        fetchAllContent();
        setEditCount(video.editCount);
        setGenerateTime(video.generateTime);
    }, [video.promptId, video.manimCodeId, video.editCount, fetchScriptFn, fetchManimCodeFn]);

    if (isLoading) {
        return <div className="w-full h-full flex items-center justify-center bg-gray-200 min-h-[200px]">
            <p className="text-gray-500">Loading...</p>
        </div>
    }
    console.log("video:", video);
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
                        <h3 className="font-bold mb-2">{title}</h3>
                        <p className="text-sm whitespace-pre-wrap">{content || 'No script available'}</p>
                    </div>
                )}
            </div>
            <div 
                className={`bg-white rounded-b-lg transition-all duration-300 ease-in-out overflow-y-auto ${
                    isHovered ? 'max-h-96 p-2 opacity-100' : 'max-h-0 p-0 opacity-0'
                }`}
            >
                <p className="text-xs text-gray-600">Edited {editCount} times</p>
                <p className="text-xs text-gray-600">Generated on {new Date(generateTime).toLocaleString()}</p>
                <p className="mt-2 font-semibold text-gray-800">Prompt:</p>
                <div className="mt-1 max-h-32 overflow-y-auto border rounded p-2 bg-gray-50">
                    <p className="text-xs font-medium text-gray-800 whitespace-pre-wrap">{script}</p>
                </div>
                <p className="mt-2 font-semibold text-gray-800">Manim Code:</p>
                <div className="mt-1 mb-2 max-h-40 overflow-y-auto border rounded p-2 bg-gray-50">
                    <p className="text-xs font-mono text-gray-800 whitespace-pre-wrap">{manimCode}</p>
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
            <Header statusText='履歴一覧' showBackButton={true} onBack={onClose} />
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4">
                {historyResult.map((video) => (
                    <HistoryCard key={video.videoId} video={video} onLoadVideo={onLoadVideo} />
                ))}
            </div>
        </div>
    )
}
