'use client'

import { useEffect, useRef, useState } from 'react'
import {
    ValidationError,
    type VideoGenerationPrompt,
    type VideoGenerationRequest,
    type VideoResult,
    validateVideoGeneration,
} from '../datas/Video'
import fetchVideo from './fetchVideo'

type AnimationResponse = {
    ok?: boolean
    video_id?: string
    message?: string
}

const stripWrappingQuotes = (value: string) => value.replace(/^['"]|['"]$/g, '')

const resolveBackendUrl = () => {
    const raw = process.env.NEXT_PUBLIC_API_URL ?? ''
    const sanitized = stripWrappingQuotes(raw).trim().replace(/\/$/, '')
    if (!sanitized) {
        throw new Error('バックエンドのURLが設定されていません')
    }
    return sanitized
}

const createVideoId = () => {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
        return crypto.randomUUID()
    }
    return `video-${Date.now()}`
}

const createVideoGenerationPrompt = (request: VideoGenerationRequest, enhancePrompt?: string): VideoGenerationPrompt => {
    const sections: string[] = [request.text]

    if (request.videoPrompt && request.videoPrompt.trim().length > 0) {
        sections.push(`【動画への追加指示】\n${request.videoPrompt.trim()}`)
    }

    if (enhancePrompt && enhancePrompt.trim().length > 0) {
        sections.push(`【再生成指示】\n${enhancePrompt.trim()}`)
    }

    return {
        prompt: sections.join('\n\n'),
        originalText: request.text,
    }
}

/**
 * UseCase層: 動画生成のビジネスロジックとAPI処理
 */
export const useVideoGeneration = () => {
    const [isGenerating, setIsGenerating] = useState(false)
    const [prompt, setPrompt] = useState<VideoGenerationPrompt | null>(null)
    const [result, setResult] = useState<VideoResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const lastRequestRef = useRef<VideoGenerationRequest | null>(null)
    const videoUrlRef = useRef<string | null>(null)

    useEffect(() => {
        return () => {
            if (videoUrlRef.current) {
                URL.revokeObjectURL(videoUrlRef.current)
            }
        }
    }, [])

    const setHandledError = (err: unknown, fallbackMessage: string) => {
        const message = err instanceof Error ? err.message : fallbackMessage
        setError(message)
        return err
    }

    const validateRequestOrThrow = (request: VideoGenerationRequest) => {
        const validation = validateVideoGeneration(request)
        if (!validation.isValid) {
            throw new ValidationError(validation.errors)
        }
    }

    const requestAnimation = async (videoId: string, content: string, enhancePrompt?: string) => {
        const baseUrl = resolveBackendUrl()
        const response = await fetch(`${baseUrl}/api/animation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: videoId,
                content,
                enhance_prompt: enhancePrompt ?? '',
            }),
        })

        let data: AnimationResponse | null = null
        try {
            data = (await response.json()) as AnimationResponse
        } catch {
            data = null
        }

        if (!response.ok) {
            throw new Error(data?.message ?? '動画生成リクエストに失敗しました')
        }

        if (!data?.ok) {
            throw new Error(data?.message ?? '動画生成に失敗しました')
        }

        return data.video_id ?? videoId
    }

    const replaceVideoUrl = async (videoId: string) => {
        const videoUrl = await fetchVideo(videoId)
        if (!videoUrl) {
            throw new Error('動画の取得に失敗しました')
        }

        if (videoUrlRef.current) {
            URL.revokeObjectURL(videoUrlRef.current)
        }

        videoUrlRef.current = videoUrl
        return videoUrl
    }

    /**
     * ランディングから動画生成完了までを一括で実行
     */
    const startVideoGeneration = async (text: string, videoPrompt?: string) => {
        try {
            const request: VideoGenerationRequest = { text, videoPrompt }
            validateRequestOrThrow(request)

            const videoId = createVideoId()
            lastRequestRef.current = request

            setIsGenerating(true)
            setError(null)
            setPrompt(null)
            setResult(null)

            const nextPrompt = createVideoGenerationPrompt(request)

            await requestAnimation(videoId, request.text, request.videoPrompt)
            const videoUrl = await replaceVideoUrl(videoId)

            const generatedResult: VideoResult = {
                videoId,
                videoUrl,
                prompt: nextPrompt,
                generatedAt: new Date(),
            }

            setPrompt(nextPrompt)
            setResult(generatedResult)
            return generatedResult
        } catch (err) {
            setPrompt(null)
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
        validateRequestOrThrow(request)

        setIsGenerating(true)
        setError(null)

        try {
            const generatedPrompt = createVideoGenerationPrompt(request)
            setPrompt(generatedPrompt)
            lastRequestRef.current = request
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
        const videoId = createVideoId()
        
        setIsGenerating(true)
        setError(null)

        try {
            // バックエンドに動画生成をリクエスト
            await requestAnimation(videoId, editedPrompt.originalText, editedPrompt.prompt)
            
            // 生成された動画を取得
            const videoUrl = await replaceVideoUrl(videoId)
            
            const generatedResult: VideoResult = {
                videoId,
                videoUrl,
                prompt: editedPrompt,
                generatedAt: new Date(),
            }

            setPrompt(editedPrompt)
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
        const baseRequest = lastRequestRef.current
        if (!baseRequest) {
            const err = new Error('動画の元データが存在しません')
            setHandledError(err, '動画編集中にエラーが発生しました')
            throw err
        }

        const enhancePrompt = [baseRequest.videoPrompt, editPrompt]
            .filter((value) => value && value.trim().length > 0)
            .join('\n')
            .trim() || undefined

        setIsGenerating(true)
        setError(null)

        try {
            await requestAnimation(videoId, baseRequest.text, enhancePrompt)
            const videoUrl = await replaceVideoUrl(videoId)
            const updatedPrompt = createVideoGenerationPrompt(baseRequest, enhancePrompt)

            const updatedResult: VideoResult = {
                videoId,
                videoUrl,
                prompt: updatedPrompt,
                generatedAt: new Date(),
            }

            setPrompt(updatedPrompt)
            setResult(updatedResult)
            return updatedResult
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
        if (videoUrlRef.current) {
            URL.revokeObjectURL(videoUrlRef.current)
            videoUrlRef.current = null
        }

        setPrompt(null)
        setResult(null)
        setError(null)
        lastRequestRef.current = null
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
