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

interface HistoryCardProps {
    video: VideoInfo
    onLoadVideo: (videoId: string, prompt: string) => Promise<any>
    content: string
    title: string
    manimCode: string
}

/**
 * A component to display a single video card.
 * On hover, it shows the script.
 */
function HistoryCard({ video, onLoadVideo, content, title, manimCode }: HistoryCardProps) {
    const [isHovered, setIsHovered] = useState(false)
    const [editCount] = useState<number>(video.editCount)
    const [generateTime] = useState<string>(video.generateTime)
    const [isLoading, setIsLoading] = useState(true)
    const [videoUrl, setVideoUrl] = useState<string>('')

    const handleVideoClick = async () => {
        try {
            console.log('Loading video:', video.videoId, 'with prompt:', content)
            await onLoadVideo(video.videoId, content)
        } catch (error) {
            console.error('Error loading video:', error)
        }
    }
    
    useEffect(() => {
        const fetchVideoUrl = async () => {
            setIsLoading(true)
            try {
                // 動画URLを生成
                const url = await fetchVideo(video.videoId)
                if (url) {
                    setVideoUrl(url)
                }
            } catch (error) {
                console.error('Error fetching video URL:', error)
            } finally {
                setIsLoading(false)
            }
        }
        
        fetchVideoUrl();
    }, [video.videoId]);

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
                {isHovered && false && (
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
                <p className="mt-2 font-semibold text-gray-800">{title}:</p>
                <div className="mt-1 max-h-32 overflow-y-auto border rounded p-2 bg-gray-50">
                    <p className="text-xs font-medium text-gray-800 whitespace-pre-wrap">{content}</p>
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
interface VideoData {
    content: string
    title: string
    script: string
    manimCode: string
}

export function HistoryViewer({ historyResult, onLoadVideo, onClose }: HistoryViewerProps) {
    const [basePrompt, setBasePrompt] = useState<string>('')
    const [videoDataMap, setVideoDataMap] = useState<Map<string, VideoData>>(new Map())
    const [isLoading, setIsLoading] = useState(true)
    const { fetchScript: fetchScriptFn } = fetchScript();
    const { fetchManimCode: fetchManimCodeFn } = fetchManimCode();

    useEffect(() => {
        // 全動画の情報を一度に取得
        const fetchAllData = async () => {
            if (!historyResult || historyResult.length === 0) return
            
            setIsLoading(true)
            try {
                // 最初の動画からスクリプト情報を取得（全動画共通のpromptId）
                const firstVideo = historyResult[0]
                const scriptData = await fetchScriptFn(firstVideo.promptId)
                
                if (scriptData && scriptData.message) {
                    const message = typeof scriptData.message === 'string' ? JSON.parse(scriptData.message) : scriptData.message
                    const newVideoDataMap = new Map<string, VideoData>()
                    
                    if (message && Array.isArray(message.prompt)) {
                        // ベースプロンプトを取得（最初のアイテム）
                        const firstItem = message.prompt[0]
                        if (firstItem && typeof firstItem.content === 'string' && firstItem.content !== "") {
                            setBasePrompt(firstItem.content)
                        } else if (firstItem && typeof firstItem.enhance_prompt === 'string' && firstItem.enhance_prompt !== "") {
                            setBasePrompt(firstItem.enhance_prompt)
                        }
                        
                        // 各動画のeditCountに応じた情報を抽出
                        for (const video of historyResult) {
                            const index = 3 * (video.editCount - 1)
                            const item = message.prompt[index]
                            
                            let content = ''
                            let title = 'Script'
                            let script = ''
                            
                            if (item && typeof item.content === 'string' && item.content !== "") {
                                content = item.content
                                script = item.content
                            } else if (item && typeof item.enhance_prompt === 'string' && item.enhance_prompt !== "") {
                                content = item.enhance_prompt
                                script = item.enhance_prompt
                            }
                            
                            // Manimコードを取得
                            let manimCode = ''
                            try {
                                const manimCodeData = await fetchManimCodeFn(video.manimCodeId)
                                if (manimCodeData && manimCodeData.message) {
                                    manimCode = manimCodeData.message
                                }
                            } catch (error) {
                                console.error('Error fetching manim code for', video.videoId, error)
                            }
                            
                            newVideoDataMap.set(video.videoId, { content, title, script, manimCode })
                        }
                    } else if (Array.isArray(message)) {
                        // 旧形式のメッセージ構造
                        if (message.length > 0) {
                            if (message[0]['content']) {
                                setBasePrompt(message[0]['content'])
                            } else if (message[0]['enhance_prompt']) {
                                setBasePrompt(message[0]['enhance_prompt'])
                            }
                        }
                        
                        for (const video of historyResult) {
                            const index = 3 * (video.editCount - 1)
                            let content = ''
                            let title = 'Script'
                            let script = ''
                            
                            if (message[index] && message[index]['content'] === '' && message[index]['enhance_prompt']) {
                                content = message[index]['enhance_prompt']
                                title = 'Enhance Script'
                            } else if (message[index] && message[index]['content']) {
                                content = message[index]['content']
                                script = message[index + 1] ? message[index + 1]['content'] : ''
                            }
                            
                            // Manimコードを取得
                            let manimCode = ''
                            try {
                                const manimCodeData = await fetchManimCodeFn(video.manimCodeId)
                                if (manimCodeData && manimCodeData.message) {
                                    manimCode = manimCodeData.message
                                }
                            } catch (error) {
                                console.error('Error fetching manim code for', video.videoId, error)
                            }
                            
                            newVideoDataMap.set(video.videoId, { content, title, script, manimCode })
                        }
                    }
                    
                    setVideoDataMap(newVideoDataMap)
                }
            } catch (error) {
                console.error('Error fetching all data:', error)
            } finally {
                setIsLoading(false)
            }
        }
        
        fetchAllData()
    }, [historyResult, fetchScriptFn, fetchManimCodeFn])

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

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center">
                <p className="text-gray-500">Loading video history...</p>
            </div>
        )
    }

    return (
        <div className="h-full flex flex-col">
            <Header statusText='履歴一覧' showBackButton={true} onBack={onClose} />
            <div className="flex-1 flex overflow-hidden">
                {/* 左側: 動画グリッド */}
                <div className="flex-1 overflow-y-auto p-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {historyResult.map((video) => {
                            const videoData = videoDataMap.get(video.videoId) || {
                                content: '',
                                title: 'Script',
                                script: '',
                                manimCode: ''
                            }
                            return (
                                <HistoryCard 
                                    key={video.videoId} 
                                    video={video} 
                                    onLoadVideo={onLoadVideo}
                                    content={videoData.content}
                                    title={videoData.title}
                                    manimCode={videoData.manimCode}
                                />
                            )
                        })}
                    </div>
                </div>
                
                {/* 右側: ベースプロンプト表示 */}
                <div className="w-96 border-l border-gray-300 bg-white overflow-y-auto p-4">
                    <h2 className="text-lg font-bold mb-4 text-gray-800">Base Prompt</h2>
                    <div className="bg-gray-50 border rounded p-4">
                        <p className="text-sm text-gray-800 whitespace-pre-wrap">{basePrompt || 'No base prompt available'}</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
