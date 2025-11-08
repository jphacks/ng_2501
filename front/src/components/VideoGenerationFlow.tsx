'use client'

import { useState } from 'react'
import type { VideoData } from '@/app/datas/Video'
import { useVideoGeneration } from '../app/hooks/useTextAnalysis'
import { Generating } from './generating/Generating'
import { Landing } from './landing/Landing'
import { Prompt } from './prompt/Prompt'
import { Result } from './result/Result'
import { useDB } from '../app/hooks/useDB'
import { Search } from './search/Search'

// ⚠️ テスト用import（Issue#58）
// この import を削除すると、テスト用ボタンが表示されなくなります
// import { TestVideoLoader } from './__test_utils__/TestVideoLoader'

/**
 * Presentation層: 状態管理
 * 4つの状態を管理: ランディング、プロンプト確認、動画生成中、リザルト
 * 状態遷移とルーティングを担当
 */
export function VideoGenerationFlow() {
    const { isGenerating, prompt, result, error, generatePrompt, generateVideo, editVideo, loadExistingVideoTest, loadExistingVideo, clearResult } = useVideoGeneration()
    const [searchResult, setSearchResult] = useState<VideoData[] | null>(null)
    const { searchVideo } = useDB()

    // Landing画面で送信時：プロンプトを生成してPrompt画面に遷移
    const handleLandingSubmit = async (text: string, videoPrompt?: string) => {
        await generatePrompt(text, videoPrompt)
    }

    // Prompt画面で動画生成時：動画を生成してGenerating→Result画面に遷移
    const handlePromptGenerate = async (editedPrompt: NonNullable<typeof prompt>) => {
        return await generateVideo(editedPrompt)
    }

    // ⚠️ テスト用（Issue#58）
    const handleLoadExistingVideoTest = async (videoId: string, promptText: string) => {
        await loadExistingVideoTest(videoId, promptText)
    }

    const handleSearch = async (content: string) => {
        if (!content) {
            setSearchResult(null)
            return
        }
        const results = await searchVideo(content)
        setSearchResult(results)
    }

    const clearSearchResult = () => {
        setSearchResult(null)
    }

    const isLanding = !isGenerating && !prompt && !result && !searchResult
    const isPromptScreen = !isGenerating && !!prompt && !result
    const isSearchResultsScreen = !isGenerating && !!searchResult && !result
    const isGeneratingScreen = isGenerating
    const isResult = !!result && !isGenerating
    const containerOverflowClass = isLanding ? 'overflow-hidden' : 'overflow-auto'

    return (
        <div className={`h-full flex flex-col w-full min-w-0 ${containerOverflowClass}`}>
            {/* 状態1: ランディング（テキスト入力） */}
            {isLanding && (
                <Landing onSubmit={handleLandingSubmit} onSearch={handleSearch} isGenerating={isGenerating} error={error}>
                    {/* ⚠️ テスト用（Issue#58） */}
                    {/* <TestVideoLoader onLoadVideo={handleLoadExistingVideo} isLoading={isGenerating} /> */}
                </Landing>
            )}

            {/* 状態2-1: プロンプト確認・編集 */}
            {isPromptScreen && prompt && <Prompt prompt={prompt} isGenerating={isGenerating} onGenerate={handlePromptGenerate} onReset={clearResult} />}

            {/* 状態2-2: 検索結果 */}
            {isSearchResultsScreen && searchResult && (
                <Search result={searchResult} isGenerating={isGenerating} onLoadVideo={loadExistingVideo} onReset={clearSearchResult} />
            )}

            {/* 状態3: 動画生成中 */}
            {isGeneratingScreen && <Generating />}

            {/* 状態4: リザルト */}
            {isResult && result && <Result result={result} isGenerating={isGenerating} onEdit={editVideo} onReset={clearResult} />}
        </div>
    )
}
