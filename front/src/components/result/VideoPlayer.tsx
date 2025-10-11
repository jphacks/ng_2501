'use client'

interface VideoPlayerProps {
    videoUrl: string
}

/**
 * Presentation層: リザルト専用の動画プレイヤー
 * シンプルで機能優先
 */
export function VideoPlayer({ videoUrl }: VideoPlayerProps) {
    return (
        <div className="bg-black rounded overflow-hidden border border-gray-300">
            <div className="aspect-video">
                <video 
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
    )
}
