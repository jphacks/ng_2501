'use client'

import { useState } from 'react'
import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Prompt } from './prompt/Prompt'
import { Result } from './result/Result'

// ⚠️ テスト用import（開発時のみ使用）
import { TestVideoLoader } from './__test_utils__/TestVideoLoader'
import { useTestVideoGeneration } from './__test_utils__/useTestVideoGeneration'

// テストモードの判定（開発環境でのみ有効）
const USE_TEST_MODE = process.env.NODE_ENV === 'development'

/**
 * Presentation層: 状態管理
 * 4つの状態を管理: ランディング、プロンプト確認、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    // テストモードの切り替え（開発環境でのみ）
    const [isTestMode, setIsTestMode] = useState(false)

    // 本番用のhook
    const productionHook = useVideoGeneration()
    
    // テスト用のhook
    const testHook = useTestVideoGeneration()

    // 使用するhookを切り替え
    const { 
        isGenerating, 
        prompt, 
        result, 
        error, 
        clearResult 
    } = isTestMode ? testHook : productionHook

    // Landing画面で送信時：プロンプトを生成してPrompt画面に遷移
    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await productionHook.generatePrompt(text, videoPrompt)
    }

    // ⚠️ テスト用：既存動画を読み込んでPrompt画面から始める
    const handleLoadExistingVideo = async (videoId: string, promptText: string) => {
        setIsTestMode(true)
        await testHook.loadExistingVideo(videoId, promptText)
    }

    // Prompt画面で動画生成時：動画を生成してGenerating→Result画面に遷移
    const handlePromptGenerate = async (editedPrompt: NonNullable<typeof prompt>) => {
        if (isTestMode) {
            return await testHook.generateVideo(editedPrompt)
        }
        return await productionHook.generateVideo(editedPrompt)
    }

    // 結果をクリア（リセットボタン）
    const handleClearResult = () => {
        setIsTestMode(false)
        productionHook.clearResult()
        testHook.clearResult()
    }

    // 動画編集（本番モードのみ）
    const handleEditVideo = async (videoId: string, editPrompt: string) => {
        if (isTestMode) {
            throw new Error('テストモードでは動画編集はできません')
        }
        return await productionHook.editVideo(videoId, editPrompt)
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
                <Landing onSubmit={handleLandingSubmit} isGenerating={isGenerating} error={error}>
                    {/* ⚠️ テスト用（開発環境のみ表示） */}
                    {USE_TEST_MODE && (
                        <TestVideoLoader 
                            onLoadVideo={handleLoadExistingVideo}
                            isLoading={isGenerating}
                        />
                    )}
                </Landing>
            )}

            {/* 状態2: プロンプト確認・編集 */}
            {isPromptScreen && prompt && (
                <Prompt prompt={prompt} isGenerating={isGenerating} onGenerate={handlePromptGenerate} />
            )}

            {/* 状態3: 動画生成中 */}
            {isGeneratingScreen && <Generating />}

            {/* 状態4: リザルト */}
            {isResult && <Result result={result} isGenerating={isGenerating} onEdit={handleEditVideo} onReset={handleClearResult} />}
        </div>
    )
}
