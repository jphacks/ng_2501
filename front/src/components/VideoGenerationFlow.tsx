'use client'

import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Result } from './result/Result'

/**
 * Presentation層: 状態管理
 * 3つの状態を管理: ランディング、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    const { isGenerating, result, error, startVideoGeneration, editVideo, clearResult } = useVideoGeneration()

    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await startVideoGeneration(text, videoPrompt)
    }

    const isLanding = !isGenerating && !result
    const isGeneratingScreen = isGenerating
    const isResult = !!result && !isGenerating
    const containerOverflowClass = isLanding ? 'overflow-hidden' : 'overflow-auto'

    return (
        <div className={`h-full flex flex-col w-full min-w-0 ${containerOverflowClass}`}>
            {/* 状態1: ランディング（テキスト入力） */}
            {isLanding && <Landing onSubmit={handleLandingSubmit} isGenerating={isGenerating} error={error} />}

            {/* 状態2: 動画生成中 */}
            {isGeneratingScreen && <Generating />}

            {/* 状態3: リザルト */}
            {isResult && <Result result={result} isGenerating={isGenerating} onEdit={editVideo} onReset={clearResult} />}
        </div>
    )
}
