'use client'

import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Prompt } from './prompt/Prompt'
import { Result } from './result/Result'

/**
 * Presentation層: 状態管理
 * 4つの状態を管理: ランディング、プロンプト確認、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    const { isGenerating, prompt, result, error, generatePrompt, generateVideo, editVideo, clearResult } =
        useVideoGeneration()

    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await generatePrompt(text, videoPrompt)
    }

    return (
        <div className="space-y-6">
            {/* 状態1: ランディング（テキスト入力） */}
            {!prompt && !result && (
                <Landing onSubmit={handleLandingSubmit} isGenerating={isGenerating} error={error} />
            )}

            {/* 状態2: プロンプト確認 */}
            {prompt && !result && !isGenerating && (
                <Prompt prompt={prompt} isGenerating={isGenerating} onGenerate={generateVideo} />
            )}

            {/* 状態3: 動画生成中 */}
            {isGenerating && prompt && !result && <Generating />}

            {/* 状態4: リザルト */}
            {result && <Result result={result} isGenerating={isGenerating} onEdit={editVideo} onReset={clearResult} />}
        </div>
    )
}
