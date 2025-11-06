'use client'

import type { VideoGenerationPrompt, VideoResult } from '@/app/datas/Video'
import { PromptEditor } from './PromptEditor'

interface PromptProps {
    prompt: VideoGenerationPrompt
    isGenerating: boolean
    onGenerate: (prompt: VideoGenerationPrompt) => Promise<VideoResult>
    onReset?: () => void
}

/**
 * Presentation層: プロンプト確認ページ全体
 */
export function Prompt({ prompt, isGenerating, onGenerate, onReset }: PromptProps) {
    return (
        <div className="h-full flex flex-col min-w-0 w-full">
            <PromptEditor prompt={prompt} isGenerating={isGenerating} onGenerate={onGenerate} onReset={onReset} />
        </div>
    )
}
