'use client'

import { useEffect, useRef, useState } from 'react'

interface VideoPlayerProps {
    videoUrl: string
}

/**
 * Presentation層: リザルト専用の動画プレイヤー
 * シンプルで機能優先、スクロール時にミニプレイヤー表示
 */
export function VideoPlayer({ videoUrl }: VideoPlayerProps) {
    const playerRef = useRef<HTMLDivElement>(null)
    const videoRef = useRef<HTMLVideoElement>(null)
    const [showMiniPlayer, setShowMiniPlayer] = useState(false)

    useEffect(() => {
        const handleScroll = () => {
            if (!playerRef.current) return

            const rect = playerRef.current.getBoundingClientRect()
            const isOutOfView = rect.bottom < 0

            setShowMiniPlayer(isOutOfView)
        }

        window.addEventListener('scroll', handleScroll, { passive: true })
        return () => window.removeEventListener('scroll', handleScroll)
    }, [])

    const scrollToPlayer = () => {
        playerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    return (
        <>
            {/* メインプレイヤー */}
            <div ref={playerRef} className="bg-black rounded overflow-hidden border border-gray-300">
                <div className="aspect-video">
                    <video
                        ref={videoRef}
                        className="w-full h-full object-contain"
                        controls
                        preload="metadata"
                    >
                        <source src={videoUrl} type="video/mp4" />
                        <track kind="captions" label="日本語" srcLang="ja" />
                        Your browser does not support the video tag.
                    </video>
                </div>
            </div>

            {/* ミニプレイヤー（スクロール時に右下表示） */}
            {showMiniPlayer && (
                <div className="fixed bottom-4 right-4 z-50 animate-fade-in">
                    <div className="bg-black rounded border-2 border-gray-300 shadow-2xl overflow-hidden">
                        <div className="relative" style={{ width: '320px' }}>
                            <div className="aspect-video">
                                <video
                                    className="w-full h-full object-contain"
                                    controls
                                    preload="metadata"
                                    onPlay={(e) => {
                                        // ミニプレイヤーで再生したらメインプレイヤーも同期
                                        if (videoRef.current && e.currentTarget !== videoRef.current) {
                                            videoRef.current.currentTime = e.currentTarget.currentTime
                                            videoRef.current.play()
                                        }
                                    }}
                                >
                                    <source src={videoUrl} type="video/mp4" />
                                    <track kind="captions" label="日本語" srcLang="ja" />
                                    Your browser does not support the video tag.
                                </video>
                            </div>

                            {/* 元の位置に戻るボタン */}
                            <button
                                type="button"
                                onClick={scrollToPlayer}
                                className="absolute top-2 right-2 bg-black/70 hover:bg-black/90 text-white p-1.5 rounded backdrop-blur-sm transition-colors"
                                title="元の位置に戻る"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>元の位置に戻る</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
