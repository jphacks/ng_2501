'use client'

interface VideoPlayerProps {
    videoUrl: string
}

/**
 * Presentation層: リザルト専用の動画プレイヤー
 */
export function VideoPlayer({ videoUrl }: VideoPlayerProps) {
    return (
        <div className="bg-gray-900 rounded-lg overflow-hidden aspect-video">
            <video className="rounded-lg h-full w-full object-contain" controls>
                <source src={videoUrl} type="video/mp4" />
                <track kind="captions" label="日本語" srcLang="ja" />
                Your browser does not support the video tag.
            </video>
        </div>
    )
}
