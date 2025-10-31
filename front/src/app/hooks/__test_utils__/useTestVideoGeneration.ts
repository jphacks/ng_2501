/**
 * ⚠️ テスト用Hook（Issue#56） ⚠️
 * 
 * このファイルはPrompt確認画面のフローをテストするための一時的なものです。
 * 
 * 目的：
 * - バックエンドで新規に動画を生成せずにPrompt→Generating→Resultフローをテストする
 * - 既存の動画を使って画面遷移とデータフローを確認する
 * 
 * 本番コードへの影響：
 * - VideoGenerationFlow.tsx で環境変数によって切り替え
 * - 開発環境(NODE_ENV=development)でのみ使用
 * - 本番環境では useVideoGeneration を使用
 */

'use client'

import { useEffect, useRef, useState } from 'react'
import type { VideoGenerationPrompt, VideoResult } from '../../datas/Video'
import fetchVideo from '../fetchVideo'

/**
 * サンプルのmanimコードを生成
 */
function createSampleManimCode(promptText: string): string {
    const truncatedText = promptText.length > 50 ? `${promptText.substring(0, 50)}...` : promptText
    return `from manim import *

class MathAnimation(Scene):
    def construct(self):
        # テスト用動画: ${truncatedText}
        
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
            // テスト用: videoIdを保持（generateVideoで使用）
            testVideoIdRef.current = videoId

            // サンプルのmanimCodeを生成
            const sampleManimCode = createSampleManimCode(promptText)
            
            const generatedPrompt: VideoGenerationPrompt = {
                prompt: promptText,
                originalText: promptText,
                manimCode: sampleManimCode,
            }

            // 状態を更新
            setPrompt(generatedPrompt)
            setResult(null)
            setError(null)
            
            return generatedPrompt
        } catch (err) {
            const message = err instanceof Error ? err.message : 'プロンプト生成中にエラーが発生しました'
            setError(message)
            throw err
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
            const message = err instanceof Error ? err.message : '動画取得中にエラーが発生しました'
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

    // 本番のuseVideoGenerationと同じインターフェースを返す
    return {
        isGenerating,
        prompt,
        result,
        error,
        // テスト用の関数
        loadExistingVideo,
        generateVideo,
        clearResult,
        // 本番で使用する関数（ダミー）
        startVideoGeneration: async () => {
            throw new Error('テストモードではstartVideoGenerationは使用できません')
        },
        generatePrompt: async () => {
            throw new Error('テストモードではgeneratePromptは使用できません')
        },
        editVideo: async () => {
            throw new Error('テストモードでは動画編集はできません')
        },
    }
}

