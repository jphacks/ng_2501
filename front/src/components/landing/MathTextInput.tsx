'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { MathEditor } from '@/components/math/MathEditor'
import { ErrorProvider } from '@/app/contexts/ErrorContext'

interface MathTextInputProps {
    onSubmit: (text: string, videoPrompt?: string) => Promise<void>
    isGenerating: boolean
}

type ViewMode = 'edit' | 'preview'

/**
 * Presentation層: 数式テキスト入力フォーム（MathEditor統合版 + プレビュー対応）
 */
export function MathTextInput({ onSubmit, isGenerating }: MathTextInputProps) {
    const [text, setText] = useState('')
    const [videoPrompt, setVideoPrompt] = useState('')
    const [showAdvanced, setShowAdvanced] = useState(false)
    const [showMathEditor, setShowMathEditor] = useState(false)
    const [currentMathValue, setCurrentMathValue] = useState('')
    const [viewMode, setViewMode] = useState<ViewMode>('edit')
    const [cursorPosition, setCursorPosition] = useState<number>(0)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!text.trim()) return
        await onSubmit(text, videoPrompt || undefined)
    }

    const handleTextAreaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setText(e.target.value)
        setCursorPosition(e.target.selectionStart)
    }

    const handleTextAreaClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
        const target = e.target as HTMLTextAreaElement
        setCursorPosition(target.selectionStart)
    }

    const handleMathEditorOpen = () => {
        setCurrentMathValue('')
        setShowMathEditor(true)
    }

    const handleMathComplete = (latex: string) => {
        if (!latex.trim()) {
            setShowMathEditor(false)
            setCurrentMathValue('')
            return
        }

        // Insert the LaTeX formula at cursor position
        const mathFormula = `$${latex}$`
        const before = text.slice(0, cursorPosition)
        const after = text.slice(cursorPosition)
        
        // Add spacing if needed
        const needSpaceBefore = before.length > 0 && !before.endsWith(' ') && !before.endsWith('\n')
        const needSpaceAfter = after.length > 0 && !after.startsWith(' ') && !after.startsWith('\n')
        
        const newText = before + 
            (needSpaceBefore ? ' ' : '') + 
            mathFormula + 
            (needSpaceAfter ? ' ' : '') + 
            after
        
        setText(newText)
        setCursorPosition(before.length + (needSpaceBefore ? 1 : 0) + mathFormula.length)
        setShowMathEditor(false)
        setCurrentMathValue('')
    }

    const handleMathCancel = () => {
        setShowMathEditor(false)
        setCurrentMathValue('')
    }

    const loadSampleText = () => {
        const sample = `# 積分の基礎

積分は、微分の逆演算として定義されます。

## 定義

関数 $f(x)$ の不定積分は以下のように表されます：

$$\\int f(x)dx = F(x) + C$$

ここで、$F'(x) = f(x)$ であり、$C$ は積分定数です。

## 具体例

1. **べき関数の積分**
   - $\\int x^2 dx = \\frac{x^3}{3} + C$
   - $\\int x^n dx = \\frac{x^{n+1}}{n+1} + C$ （$n \\neq -1$）

2. **定積分の計算**
   $$\\int_0^1 x^2 dx = \\left[\\frac{x^3}{3}\\right]_0^1 = \\frac{1}{3}$$

## 重要な性質

- **線形性**: $\\int (af(x) + bg(x))dx = a\\int f(x)dx + b\\int g(x)dx$
- **部分積分**: $\\int u dv = uv - \\int v du$
- **置換積分**: $\\int f(g(x))g'(x)dx = \\int f(u)du$ （$u = g(x)$）`
        
        setText(sample)
        setCursorPosition(sample.length)
    }

    return (
        <ErrorProvider>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    {/* ヘッダー: タブとボタン */}
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={() => setViewMode('edit')}
                                disabled={isGenerating}
                                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                                    viewMode === 'edit'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                編集
                            </button>
                            <button
                                type="button"
                                onClick={() => setViewMode('preview')}
                                disabled={isGenerating || !text.trim()}
                                className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                                    viewMode === 'preview'
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                プレビュー
                            </button>
                        </div>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={loadSampleText}
                                disabled={isGenerating}
                                className="text-sm text-green-600 hover:text-green-800 font-medium disabled:text-gray-400"
                            >
                                📝 サンプル
                            </button>
                            <button
                                type="button"
                                onClick={handleMathEditorOpen}
                                disabled={isGenerating || viewMode === 'preview'}
                                className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:text-gray-400"
                            >
                                ＋ 数式を入力
                            </button>
                        </div>
                    </div>

                    {/* 編集モード */}
                    {viewMode === 'edit' && (
                        <textarea
                            id="math-text"
                            value={text}
                            onChange={handleTextAreaChange}
                            onClick={handleTextAreaClick}
                            onKeyUp={handleTextAreaClick}
                            placeholder="例: 積分の定義について説明します。&#10;&#10;数式はLaTeX形式で入力できます：&#10;- インライン数式: $\int f(x)dx$&#10;- ブロック数式: $$\int_0^1 x^2 dx = \frac{1}{3}$$&#10;&#10;Markdown記法にも対応しています（見出し、箇条書き、強調など）"
                            className="w-full p-4 border border-gray-300 rounded-lg h-64 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                            disabled={isGenerating}
                        />
                    )}

                    {/* プレビューモード */}
                    {viewMode === 'preview' && (
                        <div className="w-full p-4 border border-gray-300 rounded-lg h-64 overflow-y-auto bg-white prose prose-sm max-w-none">
                            {text.trim() ? (
                                <ReactMarkdown
                                    remarkPlugins={[remarkMath, remarkGfm]}
                                    rehypePlugins={[rehypeKatex]}
                                    components={{
                                        // カスタムスタイリング
                                        h1: ({ node, ...props }) => (
                                            <h1 className="text-2xl font-bold mb-4 text-gray-900" {...props} />
                                        ),
                                        h2: ({ node, ...props }) => (
                                            <h2 className="text-xl font-bold mb-3 text-gray-900" {...props} />
                                        ),
                                        h3: ({ node, ...props }) => (
                                            <h3 className="text-lg font-bold mb-2 text-gray-900" {...props} />
                                        ),
                                        p: ({ node, ...props }) => (
                                            <p className="mb-3 text-gray-700 leading-relaxed" {...props} />
                                        ),
                                        ul: ({ node, ...props }) => (
                                            <ul className="list-disc list-inside mb-3 text-gray-700" {...props} />
                                        ),
                                        ol: ({ node, ...props }) => (
                                            <ol className="list-decimal list-inside mb-3 text-gray-700" {...props} />
                                        ),
                                        code: ({ node, inline, ...props }) =>
                                            inline ? (
                                                <code
                                                    className="px-1 py-0.5 bg-gray-100 text-pink-600 rounded text-sm font-mono"
                                                    {...props}
                                                />
                                            ) : (
                                                <code
                                                    className="block p-3 bg-gray-100 rounded text-sm font-mono overflow-x-auto"
                                                    {...props}
                                                />
                                            ),
                                    }}
                                >
                                    {text}
                                </ReactMarkdown>
                            ) : (
                                <p className="text-gray-400 italic">プレビューするテキストを入力してください</p>
                            )}
                        </div>
                    )}

                    {/* ヘルプテキスト */}
                    <p className="mt-2 text-xs text-gray-600">
                        {viewMode === 'edit' ? (
                            <>
                                LaTeX数式: インライン <code className="px-1 bg-gray-100">$...$</code> ブロック{' '}
                                <code className="px-1 bg-gray-100">$$...$$</code> | Markdown記法対応
                            </>
                        ) : (
                            <>数式とMarkdownのレンダリング結果を表示しています</>
                        )}
                    </p>
                </div>

                {/* 数式エディタ（編集モードのみ） */}
                {showMathEditor && viewMode === 'edit' && (
                    <div className="p-4 border border-blue-300 rounded-lg bg-blue-50">
                        <h3 className="text-sm font-medium text-gray-700 mb-3">数式エディタ</h3>
                        <MathEditor
                            value={currentMathValue}
                            onChange={setCurrentMathValue}
                            onComplete={() => handleMathComplete(currentMathValue)}
                            onCancel={handleMathCancel}
                            isVisible={true}
                        />
                        <p className="mt-2 text-xs text-gray-600">
                            Enterキーで確定、Escキーでキャンセルできます。数式は自動的に $ で囲まれます。
                        </p>
                    </div>
                )}

                {/* 詳細設定（トグル） */}
                <div>
                    <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                        <span>{showAdvanced ? '▼' : '▶'}</span>
                        詳細設定（任意）
                    </button>
                    {showAdvanced && (
                        <div className="mt-3">
                            <label
                                htmlFor="video-prompt"
                                className="block text-sm font-medium text-gray-700 mb-2"
                            >
                                動画の追加プロンプト
                            </label>
                            <textarea
                                id="video-prompt"
                                value={videoPrompt}
                                onChange={(e) => setVideoPrompt(e.target.value)}
                                placeholder="例: 〇〇の数式を強調してほしい、〇〇の文字を青くしてほしい"
                                className="w-full p-4 border border-gray-300 rounded-lg h-24 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                disabled={isGenerating}
                            />
                        </div>
                    )}
                </div>

                <button
                    type="submit"
                    disabled={!text.trim() || isGenerating}
                    className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                    {isGenerating ? 'プロンプト生成中...' : 'プロンプトを生成'}
                </button>
            </form>
        </ErrorProvider>
    )
}
