/**
 * ⚠️ テスト用Hook ⚠️
 * 
 * このファイルはPrompt確認画面のフローをテストするための一時的なものです。
 * 
 * 目的：
 * - バックエンドで新規に動画を生成せずにPrompt→Generating→Resultフローをテストする
 * - 既存の動画を使って画面遷移とデータフローを確認する
 * 
 * 削除時の影響：
 * - このファイルを削除しても本番コードには影響しません
 */

'use client'

import { useEffect, useRef, useState } from 'react'
import type { VideoGenerationPrompt, VideoResult } from '../../app/datas/Video'
import fetchVideo from '../../app/hooks/fetchVideo'

/**
 * テスト用: 既存動画を使った動画生成フローのシミュレーション
 */
export const useTestVideoGeneration = () => {
    const [isGenerating, setIsGenerating] = useState(false)
    const [prompt, setPrompt] = useState<VideoGenerationPrompt | null>(null)
    const [result, setResult] = useState<VideoResult | null>(null)
    const [error, setError] = useState<string | null>(null)
    const videoUrlRef = useRef<string | null>(null)
    const testVideoIdRef = useRef<string | null>(null)

    useEffect(() => {
        return () => {
            if (videoUrlRef.current) {
                URL.revokeObjectURL(videoUrlRef.current)
            }
        }
    }, [])

    /**
     * 既存動画IDを保持してPrompt画面を表示
     */
    const loadExistingVideo = async (videoId: string, promptText: string = '既存の動画') => {
        try {
            setIsGenerating(true)
            setError(null)
            setPrompt(null)
            setResult(null)

            // テスト用: videoIdを保持（generateVideoで使用）
            testVideoIdRef.current = videoId

            // サンプルのmanimCodeを生成
            const sampleManimCode = createSampleManimCode(promptText)
            
            const prompt: VideoGenerationPrompt = {
                prompt: promptText,
                originalText: promptText,
                manimCode: sampleManimCode,
            }

            setPrompt(prompt)
            return prompt
        } catch (err) {
            const message = err instanceof Error ? err.message : 'プロンプト生成中にエラーが発生しました'
            setError(message)
            throw err
        } finally {
            setIsGenerating(false)
        }
    }

    /**
     * 既存動画をfetch（新規生成はしない）
     */
    const generateVideo = async (editedPrompt: VideoGenerationPrompt) => {
        if (!testVideoIdRef.current) {
            throw new Error('テスト用の動画IDが設定されていません')
        }

        const videoId = testVideoIdRef.current
        
        setIsGenerating(true)
        setError(null)

        try {
            // 既存動画を取得
            const videoUrl = await fetchVideo(videoId)
            if (!videoUrl) {
                throw new Error('動画の取得に失敗しました')
            }

            if (videoUrlRef.current) {
                URL.revokeObjectURL(videoUrlRef.current)
            }
            videoUrlRef.current = videoUrl
            
            const generatedResult: VideoResult = {
                videoId,
                videoUrl,
                prompt: editedPrompt,
                generatedAt: new Date(),
            }

            setPrompt(editedPrompt)
            setResult(generatedResult)
            testVideoIdRef.current = null // 使用後はクリア
            return generatedResult
        } catch (err) {
            const message = err instanceof Error ? err.message : '動画生成中にエラーが発生しました'
            setError(message)
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
        testVideoIdRef.current = null
    }

    return {
        isGenerating,
        prompt,
        result,
        error,
        loadExistingVideo,
        generateVideo,
        clearResult,
    }
}

/**
 * サンプルのmanimコードを生成
 */
function createSampleManimCode(promptText: string): string {
    return `from manim import *

class MathAnimation(Scene):
    def construct(self):
        # テスト用動画: ${promptText.substring(0, 50)}${promptText.length > 50 ? '...' : ''}
        
        # タイトル
        title = Text("数式アニメーション", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))
        
        # 数式の表示（例）
        equation = MathTex(r"\\\\int_0^1 x^2 dx = \\\\frac{1}{3}")
        self.play(Write(equation))
        self.wait(2)
        
        # フェードアウト
        self.play(FadeOut(equation))
        self.wait(1)`
}

