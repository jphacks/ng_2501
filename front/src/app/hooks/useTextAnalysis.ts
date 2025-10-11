'use client'

import { useState } from 'react'
import {
    ValidationError,
    type VideoEditRequest,
    type VideoGenerationPrompt,
    type VideoGenerationRequest,
    type VideoResult,
    validateVideoEdit,
    validateVideoGeneration,
} from '../datas/Video'

/**
 * UseCase層: 動画生成のビジネスロジックとAPI処理
 */
export const useVideoGeneration = () => {
    const [isGenerating, setIsGenerating] = useState(false)
    const [prompt, setPrompt] = useState<VideoGenerationPrompt | null>(null)
    const [result, setResult] = useState<VideoResult | null>(null)
    const [error, setError] = useState<string | null>(null)

    const setHandledError = (err: unknown, fallbackMessage: string) => {
        const message = err instanceof Error ? err.message : fallbackMessage
        setError(message)
        return err
    }

    const createPrompt = async (request: VideoGenerationRequest): Promise<VideoGenerationPrompt> => {
        const validation = validateVideoGeneration(request)
        if (!validation.isValid) {
            throw new ValidationError(validation.errors)
        }

        // TODO: 実際のAPI呼び出しに置き換える
        // const response = await fetch('/api/generate-prompt', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(request)
        // })
        // const data = await response.json()

        // 模擬的な処理（実装時に削除）
        await new Promise((resolve) => setTimeout(resolve, 2000))

        // 模擬的な結果（実装時に削除）
        return {
            prompt: `${request.text}の数式を視覚的に解説する動画を生成します。${request.videoPrompt ? `追加指示: ${request.videoPrompt}` : ''}`,
            manimCode: '# Manim code will be generated here',
            originalText: request.text,
        }
    }

    const createVideo = async (generationPrompt: VideoGenerationPrompt): Promise<VideoResult> => {
        // TODO: 実際のAPI呼び出しに置き換える
        // const response = await fetch('/api/generate-video', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(generationPrompt)
        // })
        // const data = await response.json()

        // 模擬的な処理（実装時に削除）
        await new Promise((resolve) => setTimeout(resolve, 3000))

        // 模擬的な結果（実装時に削除）
        return {
            videoUrl: '/mock-video.mp4',
            prompt: generationPrompt,
            generatedAt: new Date(),
        }
    }

    /**
     * ランディングから動画生成完了までを一括で実行
     */
    const startVideoGeneration = async (text: string, videoPrompt?: string) => {
        const request: VideoGenerationRequest = { text, videoPrompt }

        setIsGenerating(true)
        setError(null)
        setPrompt(null)
        setResult(null)

        try {
            const generatedPrompt = await createPrompt(request)
            setPrompt(generatedPrompt)
            const generatedResult = await createVideo(generatedPrompt)
            setResult(generatedResult)
            return generatedResult
        } catch (err) {
            setHandledError(err, '動画生成中にエラーが発生しました')
            throw err
        } finally {
            setIsGenerating(false)
        }
    }

    /**
     * プロンプトを生成
     */
    const generatePrompt = async (text: string, videoPrompt?: string) => {
        const request: VideoGenerationRequest = { text, videoPrompt }

        setIsGenerating(true)
        setError(null)
        setPrompt(null)

        try {
            const generatedPrompt = await createPrompt(request)
            setPrompt(generatedPrompt)
            return generatedPrompt
        } catch (err) {
            setHandledError(err, 'プロンプト生成中にエラーが発生しました')
            throw err
        } finally {
            setIsGenerating(false)
        }
    }

    /**
     * 動画を生成
     */
    const generateVideo = async (editedPrompt: VideoGenerationPrompt) => {
        setIsGenerating(true)
        setError(null)

        try {
            setPrompt(editedPrompt)
            const generatedResult = await createVideo(editedPrompt)
            setResult(generatedResult)
            return generatedResult
        } catch (err) {
            setHandledError(err, '動画生成中にエラーが発生しました')
            throw err
        } finally {
            setIsGenerating(false)
        }
    }

    /**
     * 動画を編集（再生成）
     */
    const editVideo = async (videoId: string, editPrompt: string) => {
        const request: VideoEditRequest = { videoId, editPrompt }

        // バリデーション
        const validation = validateVideoEdit(request)
        if (!validation.isValid) {
            setError(validation.errors.join(', '))
            throw new ValidationError(validation.errors)
        }

        setIsGenerating(true)
        setError(null)

        try {
            // TODO: 実際のAPI呼び出しに置き換える
            // const response = await fetch('/api/edit-video', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify(request)
            // })
            // const data = await response.json()

            // 模擬的な処理（実装時に削除）
            await new Promise((resolve) => setTimeout(resolve, 3000))

            // 模擬的な結果（実装時に削除）
            const mockResult: VideoResult = {
                videoUrl: '/mock-video-edited.mp4',
                prompt: {
                    prompt: editPrompt,
                    originalText: result?.prompt.originalText || '',
                },
                generatedAt: new Date(),
            }

            setResult(mockResult)
            return mockResult
        } catch (err) {
            setHandledError(err, '動画編集中にエラーが発生しました')
            throw err
        } finally {
            setIsGenerating(false)
        }
    }

    /**
     * 結果をクリア
     */
    const clearResult = () => {
        setPrompt(null)
        setResult(null)
        setError(null)
    }

    return {
        isGenerating,
        prompt,
        result,
        error,
        startVideoGeneration,
        generatePrompt,
        generateVideo,
        editVideo,
        clearResult,
    }
}
