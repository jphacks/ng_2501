'use client'

import type { VideoGenerationPrompt, VideoResult } from '../../app/datas/Video'
import { PromptEditor } from './PromptEditor'

interface PromptProps {
    prompt: VideoGenerationPrompt
    isGenerating: boolean
    onGenerate: (prompt: VideoGenerationPrompt) => Promise<VideoResult>
}

/**
 * Presentation層: プロンプト確認ページ全体
 */
export function Prompt({ prompt, isGenerating, onGenerate }: PromptProps) {
    return (
        <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">
                    ステップ2: プロンプトの確認・編集
                </h3>
                <p className="text-sm text-gray-600">
                    AIが生成したプロンプトを確認し、必要に応じて編集してください
                </p>
            </div>

            <PromptEditor prompt={prompt} isGenerating={isGenerating} onGenerate={onGenerate} />
        </div>
    )
}
