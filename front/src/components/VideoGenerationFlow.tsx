'use client'

import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Result } from './result/Result'

// ⚠️ テスト用import（Issue#56）
// この import を削除すると、テスト用ボタンが表示されなくなります
import { TestVideoLoader } from './__test_utils__/TestVideoLoader'

/**
 * Presentation層: 状態管理
 * 3つの状態を管理: ランディング、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    const { isGenerating, result, error, startVideoGeneration, editVideo, loadExistingVideo, clearResult } = useVideoGeneration()

    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await startVideoGeneration(text, videoPrompt)
    }

    // ⚠️ テスト用（Issue#56）
    const handleLoadExistingVideo = async (videoId: string, promptText: string) => {
        await loadExistingVideo(videoId, promptText)
    }

    const isLanding = !isGenerating && !result
    const isGeneratingScreen = isGenerating
    const isResult = !!result && !isGenerating
    const containerOverflowClass = isLanding ? 'overflow-hidden' : 'overflow-auto'

    return (
        <div className={`h-full flex flex-col w-full min-w-0 ${containerOverflowClass}`}>
            {/* 状態1: ランディング（テキスト入力） */}
            {isLanding && (
                <Landing 
                    onSubmit={handleLandingSubmit} 
                    isGenerating={isGenerating} 
                    error={error}
                >
                    {/* ⚠️ テスト用（Issue#56） */}
                    <TestVideoLoader 
                        onLoadVideo={handleLoadExistingVideo}
                        isLoading={isGenerating}
                    />
                </Landing>
            )}

            {/* 状態2: 動画生成中 */}
            {isGeneratingScreen && <Generating />}

            {/* 状態3: リザルト */}
            {isResult && <Result result={result} isGenerating={isGenerating} onEdit={editVideo} onReset={clearResult} />}
        </div>
    )
}
