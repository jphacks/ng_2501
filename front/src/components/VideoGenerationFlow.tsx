'use client'

import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Prompt } from './prompt/Prompt'
import { Result } from './result/Result'

// ⚠️ テスト用import（Issue#56）
// この import を削除すると、テスト用ボタンが表示されなくなります
import { TestVideoLoader } from './__test_utils__/TestVideoLoader'

/**
 * Presentation層: 状態管理
 * 4つの状態を管理: ランディング、プロンプト確認、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    const { 
        isGenerating, 
        prompt, 
        result, 
        error, 
        generatePrompt, 
        generateVideo, 
        editVideo, 
        loadExistingVideo, 
        clearResult 
    } = useVideoGeneration()

    // Landing画面で送信時：プロンプトを生成してPrompt画面に遷移
    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await generatePrompt(text, videoPrompt)
    }

    // ⚠️ テスト用（Issue#56）：既存動画を読み込んでPrompt画面から始める
    const handleLoadExistingVideo = async (videoId: string, promptText: string) => {
        await loadExistingVideo(videoId, promptText)
    }

    // Prompt画面で動画生成時：動画を生成してGenerating→Result画面に遷移
    const handlePromptGenerate = async (editedPrompt: NonNullable<typeof prompt>) => {
        return await generateVideo(editedPrompt)
    }

    // 画面の状態を判定
    const isLanding = !isGenerating && !prompt && !result
    const isPromptScreen = !isGenerating && !!prompt && !result
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

            {/* 状態2: プロンプト確認・編集 */}
            {isPromptScreen && prompt && (
                <Prompt prompt={prompt} isGenerating={isGenerating} onGenerate={handlePromptGenerate} />
            )}

            {/* 状態3: 動画生成中 */}
            {isGeneratingScreen && <Generating />}

            {/* 状態4: リザルト */}
            {isResult && <Result result={result} isGenerating={isGenerating} onEdit={editVideo} onReset={clearResult} />}
        </div>
    )
}
