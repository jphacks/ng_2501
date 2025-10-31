'use client'

import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Prompt } from './prompt/Prompt'
import { Result } from './result/Result'

// ⚠️ テスト用import（開発環境のみ）
import { TestVideoLoader } from './__test_utils__/TestVideoLoader'
import { useTestVideoGeneration } from '../app/hooks/__test_utils__/useTestVideoGeneration'

// テストモードの判定（開発環境でのみ有効）
const IS_DEVELOPMENT = process.env.NODE_ENV === 'development'

/**
 * Presentation層: 状態管理
 * 4つの状態を管理: ランディング、プロンプト確認、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    // ⚠️ 開発環境: テスト用hookと本番用hookを両方初期化
    // 本番環境: 本番用hookのみ初期化
    const productionHook = useVideoGeneration()
    const testHook = IS_DEVELOPMENT ? useTestVideoGeneration() : null

    // 通常は本番用hookを使用
    const {
        isGenerating,
        prompt,
        result,
        error,
        generatePrompt,
        generateVideo,
        editVideo,
        clearResult,
    } = productionHook

    // ⚠️ テスト用：既存動画を読み込んでPrompt画面から始める（開発環境のみ）
    const handleLoadExistingVideo = IS_DEVELOPMENT && testHook
        ? async (videoId: string, promptText: string) => {
              await testHook.loadExistingVideo(videoId, promptText)
          }
        : undefined

    // Landing画面で送信時：プロンプトを生成してPrompt画面に遷移
    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await generatePrompt(text, videoPrompt)
    }

    // Prompt画面で動画生成時：動画を生成してGenerating→Result画面に遷移
    const handlePromptGenerate = async (editedPrompt: NonNullable<typeof prompt>) => {
        // ⚠️ テストモード判定：testHookにpromptがある場合はテストフロー
        if (IS_DEVELOPMENT && testHook?.prompt) {
            return await testHook.generateVideo(editedPrompt)
        }
        return await generateVideo(editedPrompt)
    }

    // 結果をクリア
    const handleClearResult = () => {
        clearResult()
        testHook?.clearResult()
    }

    // 画面の状態を判定（testHookの状態も考慮）
    const activePrompt = testHook?.prompt || prompt
    const activeResult = testHook?.result || result
    const activeIsGenerating = testHook?.isGenerating || isGenerating

    const isLanding = !activeIsGenerating && !activePrompt && !activeResult
    const isPromptScreen = !activeIsGenerating && !!activePrompt && !activeResult
    const isGeneratingScreen = activeIsGenerating
    const isResult = !!activeResult && !activeIsGenerating

    const containerOverflowClass = isLanding ? 'overflow-hidden' : 'overflow-auto'

    return (
        <div className={`h-full flex flex-col w-full min-w-0 ${containerOverflowClass}`}>
            {/* 状態1: ランディング（テキスト入力） */}
            {isLanding && (
                <Landing onSubmit={handleLandingSubmit} isGenerating={activeIsGenerating} error={error}>
                    {/* ⚠️ テスト用（開発環境のみ表示） */}
                    {IS_DEVELOPMENT && handleLoadExistingVideo && (
                        <TestVideoLoader onLoadVideo={handleLoadExistingVideo} isLoading={activeIsGenerating} />
                    )}
                </Landing>
            )}

            {/* 状態2: プロンプト確認・編集 */}
            {isPromptScreen && activePrompt && (
                <Prompt prompt={activePrompt} isGenerating={activeIsGenerating} onGenerate={handlePromptGenerate} />
            )}

            {/* 状態3: 動画生成中 */}
            {isGeneratingScreen && <Generating />}

            {/* 状態4: リザルト */}
            {isResult && activeResult && (
                <Result
                    result={activeResult}
                    isGenerating={activeIsGenerating}
                    onEdit={editVideo}
                    onReset={handleClearResult}
                />
            )}
        </div>
    )
}
