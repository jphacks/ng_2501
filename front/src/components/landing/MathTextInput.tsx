'use client'

import { useState, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { MathEditor } from '@/components/math/MathEditor'
import { MathExpression, getMathExpressionAtPosition, replaceMathExpression } from '@/app/datas/MathExpression'
import { ErrorProvider } from '@/app/contexts/ErrorContext'
import { generateMathNoteFromTitle } from '@/app/hooks/useGeminiAPI'
import { GeminiError } from '@/app/datas/GeminiConfig'

interface MathTextInputProps {
    onSubmit: (text: string, videoPrompt?: string) => Promise<void>
    isGenerating: boolean
}

type ViewMode = 'edit' | 'preview' | 'split'

const findScrollableContainer = (element: HTMLElement | null): HTMLElement | null => {
    if (typeof window === 'undefined') {
        return null
    }

    let current: HTMLElement | null = element?.parentElement ?? null

    while (current) {
        const style = window.getComputedStyle(current)
        const canScrollY = current.scrollHeight > current.clientHeight && style.overflowY !== 'visible'
        const canScrollX = current.scrollWidth > current.clientWidth && style.overflowX !== 'visible'

        if (canScrollY || canScrollX) {
            return current
        }

        current = current.parentElement
    }

    return null
}

/**
 * プレビューパネルコンポーネント（再利用可能）
 */
function PreviewPanel({ text, className = '' }: { text: string; className?: string }) {
    return (
        <div className={`w-full p-4 border border-gray-300 rounded-lg overflow-y-auto bg-white prose prose-sm max-w-none ${className}`}>
            {text.trim() ? (
                <ReactMarkdown
                    remarkPlugins={[remarkMath, remarkGfm]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                        h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mb-4 text-gray-900" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-xl font-bold mb-3 text-gray-900" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-lg font-bold mb-2 text-gray-900" {...props} />,
                        p: ({ node, ...props }) => <p className="mb-3 text-gray-700 leading-relaxed" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-3 text-gray-700" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-3 text-gray-700" {...props} />,
                        code: ({ node, className, ...props }) => {
                            const isInline = !className || !className.startsWith('language-')
                            return isInline ? (
                                <code className="px-1 py-0.5 bg-gray-100 text-pink-600 rounded text-sm font-mono" {...props} />
                            ) : (
                                <code className="block p-3 bg-gray-100 rounded text-sm font-mono overflow-x-auto" {...props} />
                            )
                        },
                    }}
                >
                    {text}
                </ReactMarkdown>
            ) : (
                <p className="text-gray-400 italic">プレビューするテキストを入力してください</p>
            )}
        </div>
    )
}

/**
 * Presentation層: 数式テキスト入力フォーム（MathEditor統合版 + プレビュー対応）
 */
export function MathTextInput({ onSubmit, isGenerating }: MathTextInputProps) {
    const [text, setText] = useState('')
    const [videoPrompt, setVideoPrompt] = useState('')
    const [showMathEditor, setShowMathEditor] = useState(false)
    const [currentMathValue, setCurrentMathValue] = useState('')
    const [activeMathExpression, setActiveMathExpression] = useState<MathExpression | null>(null)
    const [viewMode, setViewMode] = useState<ViewMode>('edit')
    const [cursorPosition, setCursorPosition] = useState<number>(0)
    const [titleInput, setTitleInput] = useState('')
    const [isGeneratingContent, setIsGeneratingContent] = useState(false)
    const [generationError, setGenerationError] = useState<string | null>(null)

    const textAreaRef = useRef<HTMLTextAreaElement>(null)
    const [popupPosition, setPopupPosition] = useState<{ top: number; left: number } | null>(null)
    const [showInlinePopup, setShowInlinePopup] = useState(false)

    const isDeleteOperationRef = useRef(false)
    const openedByDollarKeyRef = useRef(false) // 「$」キーで開いたかどうか

    // カーソル位置からのポップアップの座標を計算
    const calculatePopupPosition = useCallback(() => {
        if (!textAreaRef.current) return null

        const textArea = textAreaRef.current
        const { selectionStart } = textArea
        const textBeforeCursor = textArea.value.substring(0, selectionStart)

        // 行数計算
        const lines = textBeforeCursor.split('\n')
        const currentLine = lines.length - 1
        const currentColumn = lines[lines.length - 1].length

        // テキストエリアのスタイル情報を取得
        const computedStyle = window.getComputedStyle(textArea)
        const lineHeight = parseInt(computedStyle.lineHeight || '20', 10)
        const fontSize = parseInt(computedStyle.fontSize || '14', 10)
        const paddingTop = parseInt(computedStyle.paddingTop || '0', 10)
        const paddingLeft = parseInt(computedStyle.paddingLeft || '0', 10)

        // テキストエリアの位置を取得
        const rect = textArea.getBoundingClientRect()

        // カーソルの概算位置を計算
        const charWidth = fontSize * 0.6
        const cursorTop = rect.top + paddingTop + currentLine * lineHeight
        const cursorLeft = rect.left + paddingLeft + currentColumn * charWidth

        const verticalOffset = 240 // keep popup slightly further away from the detected math
        return {
            top: Math.min(cursorTop, rect.bottom - 20) - verticalOffset,
            left: Math.max(rect.left, Math.min(cursorLeft, rect.right - 300)) - 40,
        }
    }, [])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!text.trim()) return
        await onSubmit(text, videoPrompt || undefined)
    }

    const handleTextAreaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        // 自動で「$」や「$$」を追加するロジックは削除（手入力 + ポップアップオープンに統一）
        const input = e.target.value
        const cursorPos = e.target.selectionStart

        setText(input)
        setCursorPosition(cursorPos)

        if (showInlinePopup) {
            const position = calculatePopupPosition()
            setPopupPosition(position)
        }

        if (showMathEditor) {
            setShowInlinePopup(false)
        } else {
            judgeShowPopup(input, cursorPos)
        }
    }

    const judgeShowPopup = (input: string, cursorPos: number) => {
        const expression = getMathExpressionAtPosition(input, cursorPos)

        if (expression) {
            setActiveMathExpression(expression)
            setCurrentMathValue(expression.latex)
            const position = calculatePopupPosition()
            setPopupPosition(position)
            setShowInlinePopup(true)
            setShowMathEditor(true)
            openedByDollarKeyRef.current = false
            return
        }

        setActiveMathExpression(null)
        setShowMathEditor(false)
        setShowInlinePopup(false)
        setCurrentMathValue('')
        setPopupPosition(null)
    }

    // ぶら下がった $$ を削除（カーソルの直前/直後が $ で挟まれているケース）
    const cleanupDanglingDollars = (baseCursorPos?: number) => {
        let pos = baseCursorPos ?? cursorPosition
        if (pos < 0) pos = 0
        if (pos > text.length) pos = text.length

        if (pos > 0 && pos < text.length && text[pos - 1] === '$' && text[pos] === '$') {
            const before = text.slice(0, pos - 1)
            const after = text.slice(pos + 1)
            const newText = before + after
            const newCursor = pos - 1
            setText(newText)
            setCursorPosition(newCursor)
            setTimeout(() => {
                const ta = textAreaRef.current
                if (ta) {
                    ta.focus({ preventScroll: true })
                    ta.setSelectionRange(newCursor, newCursor)
                }
            }, 0)
        }
    }

    // 数式（$...$ / $$...$$）全体を削除し、前後のスペース重複を詰める
    const removeActiveMathExpression = (expr: MathExpression) => {
        const start = expr.start
        const end = expr.end
        const before = text.slice(0, start)
        const after = text.slice(end)

        let newText: string
        if (before.endsWith(' ') && after.startsWith(' ')) {
            newText = before.slice(0, -1) + after // スペースを1つに詰める
        } else {
            newText = before + after
        }

        setText(newText)
        setCursorPosition(start)

        setTimeout(() => {
            const ta = textAreaRef.current
            if (ta) {
                ta.focus({ preventScroll: true })
                ta.setSelectionRange(start, start)
            }
        }, 0)
    }

    const handleTextAreaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Delete, Backspace, Cut操作を検出
        if (e.key === 'Delete' || e.key === 'Backspace' || (e.ctrlKey && e.key.toLowerCase() === 'x')) {
            isDeleteOperationRef.current = true
        } else {
            isDeleteOperationRef.current = false
        }

        // 「$」が押されたら、その場で数式エディタを開く（文字入力は阻止）
        if (e.key === '$' && viewMode !== 'preview' && !isGenerating) {
            e.preventDefault()

            const target = e.target as HTMLTextAreaElement
            const pos = target.selectionStart
            setCursorPosition(pos)

            setCurrentMathValue('')
            setActiveMathExpression(null)

            const position = calculatePopupPosition()
            setPopupPosition(position)
            setShowInlinePopup(true)
            setShowMathEditor(true)
            openedByDollarKeyRef.current = true
            return
        }

        // 矢印等でカーソル移動
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'PageUp', 'PageDown'].includes(e.key)) {
            setTimeout(() => {
                const target = e.target as HTMLTextAreaElement
                const newCursorPosition = target.selectionStart
                setCursorPosition(newCursorPosition)
                judgeShowPopup(text, newCursorPosition)

                if (showInlinePopup) {
                    const position = calculatePopupPosition()
                    setPopupPosition(position)
                }
            }, 0)
        }
    }

    const handleTextAreaClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
        const target = e.target as HTMLTextAreaElement
        setCursorPosition(target.selectionStart)
        judgeShowPopup(text, target.selectionStart)
    }

    const handleMathEditorOpen = () => {
        if (viewMode === 'preview') return

        setCurrentMathValue('')
        setActiveMathExpression(null)

        const position = calculatePopupPosition()
        setPopupPosition(position)
        setShowInlinePopup(true)
        setShowMathEditor(true)
        openedByDollarKeyRef.current = false
    }

    const handleMathComplete = (latex: string) => {
        // ===== 空で確定：囲み削除 or ぶら下がり $$ の掃除 =====
        if (!latex.trim()) {
            const textArea = textAreaRef.current
            const prevTop = textArea?.scrollTop ?? 0
            const prevLeft = textArea?.scrollLeft ?? 0

            if (activeMathExpression) {
                // 既存の数式を編集中 → `$...$`（または `$$...$$`）ごと削除
                removeActiveMathExpression(activeMathExpression)
            } else {
                // 「$」起点などで空確定 → もし $$ が残っていれば削除
                cleanupDanglingDollars()
            }

            // 共通でポップアップを閉じる
            setShowMathEditor(false)
            setShowInlinePopup(false)
            setCurrentMathValue('')
            setActiveMathExpression(null)
            setPopupPosition(null)

            // フォーカス・スクロール復元
            setTimeout(() => {
                const ta = textAreaRef.current
                if (ta) {
                    ta.focus({ preventScroll: true })
                    ta.scrollTop = prevTop
                    ta.scrollLeft = prevLeft
                }
            }, 0)
            return
        }
        // ===== 空でない：通常の確定フロー =====

        const textArea = textAreaRef.current
        const previousScrollTop = textArea?.scrollTop ?? 0
        const previousScrollLeft = textArea?.scrollLeft ?? 0
        const scrollableParent = textArea ? findScrollableContainer(textArea) : null
        const parentScrollTop = scrollableParent?.scrollTop ?? 0
        const parentScrollLeft = scrollableParent?.scrollLeft ?? 0

        let newText = text
        let newCursorPosition = cursorPosition

        if (activeMathExpression) {
            newText = replaceMathExpression(text, activeMathExpression, latex)
            const updatedExpression = getMathExpressionAtPosition(newText, activeMathExpression.start + 1)
            newCursorPosition = updatedExpression ? updatedExpression.end : activeMathExpression.start + latex.length
        } else {
            // 新規挿入：$...$
            const mathFormula = `$${latex}$`
            const before = text.slice(0, cursorPosition)
            const after = text.slice(cursorPosition)

            const needSpaceBefore = before.length > 0 && !before.endsWith(' ') && !before.endsWith('\n')
            const needSpaceAfter = after.length > 0 && !after.startsWith(' ') && !after.startsWith('\n')

            const textToInsert = (needSpaceBefore ? ' ' : '') + mathFormula + (needSpaceAfter ? ' ' : '')
            newText = before + textToInsert + after
            newCursorPosition = cursorPosition + (needSpaceBefore ? 1 : 0) + mathFormula.length
        }

        setText(newText)
        setCursorPosition(newCursorPosition)

        setShowMathEditor(false)
        setShowInlinePopup(false)
        setCurrentMathValue('')
        setActiveMathExpression(null)
        setPopupPosition(null)
        openedByDollarKeyRef.current = false

        const restoreFocusAndSelection = () => {
            const target = textAreaRef.current
            if (!target) return
            target.focus({ preventScroll: true })
            target.setSelectionRange(newCursorPosition, newCursorPosition)
            target.scrollTop = previousScrollTop
            target.scrollLeft = previousScrollLeft

            const parent = scrollableParent ?? findScrollableContainer(target)
            if (parent) {
                parent.scrollTop = parentScrollTop
                parent.scrollLeft = parentScrollLeft
            }
        }

        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(restoreFocusAndSelection)
        } else {
            setTimeout(restoreFocusAndSelection, 0)
        }
    }

    const handleMathCancel = () => {
        setShowMathEditor(false)
        setShowInlinePopup(false)
        setCurrentMathValue('')
        setActiveMathExpression(null)
        setPopupPosition(null)

        // 「$」で開いて空のままキャンセル等で $$ が残る可能性に備え、掃除
        cleanupDanglingDollars()

        setTimeout(() => {
            textAreaRef.current?.focus()
        }, 100)
    }

    const placeholderText = `# 二次方程式の解の公式

二次方程式 $ax^2 + bx + c = 0$ の解は、次の公式で求められます：

$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$

## 導出過程

1. 両辺を $a$ で割る
2. 平方完成を行う
3. 両辺の平方根をとる

判別式 $D = b^2 - 4ac$ の値によって、解の個数が決まります。`

    const loadSampleText = () => {
        if (text.trim() && !window.confirm('現在の入力内容が削除されます。サンプルを読み込みますか？')) {
            return
        }

        const sample = `# 三角関数の"動き"を単位円で体感しよう
## 1. 単位円で三角関数スタート！

まず半径1（原点中心）の円＝**単位円**を用意しよう。  

- x軸の正の方向（右向き）を0°、そこから反時計回りに角度 $\\theta$ をとる。
- このとき単位円上の点 $P$ の座標は

$$P(\\cos\\theta,\\,\\sin\\theta)$$

  - 横：$\\cos\\theta$
  - 縦：$\\sin\\theta$

**POINT:** どの $\\theta$ でも $\\cos^2\\theta+\\sin^2\\theta=1$。  
これは**三角関数の基本式**だね！

---

## 2. "角度を90°（$\\frac{\\pi}{2}$）ずらす"ってどういうこと？

次に、点 $P$ を角度90°、つまり $\\frac{\\pi}{2}$ 進めてみよう。

- 回転後の座標

$$Q\\left(\\cos\\left(\\theta+\\frac{\\pi}{2}\\right),\\,\\sin\\left(\\theta+\\frac{\\pi}{2}\\right)\\right)$$

- 実は、これは

$$Q(-\\sin\\theta,\\,\\cos\\theta)$$

となる！

**POINT:** "$\\cos\\theta$"の成分が"$-\\sin\\theta$"に、"$\\sin\\theta$"が"$\\cos\\theta$"に。それぞれ"入れ替わり、横はマイナス"されてるね。`

        setText(sample)
        setCursorPosition(sample.length)
    }

    const handleGenerateFromTitle = async () => {
        if (!titleInput.trim()) {
            setGenerationError('タイトルを入力してください')
            return
        }

        setIsGeneratingContent(true)
        setGenerationError(null)
        setViewMode('edit')

        try {
            const result = await generateMathNoteFromTitle(titleInput)

            const generatedText = `# ${titleInput}\n\n${result.content}`
            setText(generatedText)
            setCursorPosition(generatedText.length)
            setTitleInput('')

            setTimeout(() => {
                setViewMode('split')
            }, 100)
        } catch (error) {
            if (error instanceof GeminiError) {
                setGenerationError(error.message)
            } else if (error instanceof Error) {
                setGenerationError(`エラーが発生しました: ${error.message}`)
            } else {
                setGenerationError('予期しないエラーが発生しました')
            }
            console.error('Generation error:', error)
        } finally {
            setIsGeneratingContent(false)
        }
    }

    return (
        <ErrorProvider>
            <form onSubmit={handleSubmit} className="flex flex-col h-full min-w-0">
                {/* 数式エディタポップアップ */}
                {showInlinePopup && showMathEditor && popupPosition && (
                    <div
                        className="fixed z-50 bg-white border border-gray-300 rounded shadow-xl w-[500px]"
                        style={{ top: `${popupPosition.top}px`, left: `${popupPosition.left}px` }}
                    >
                        {/* ヘッダー */}
                        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
                            <h3 className="text-sm font-semibold text-gray-800">数式を入力</h3>
                            <button
                                type="button"
                                onClick={handleMathCancel}
                                className="text-gray-400 hover:text-gray-600 transition-colors"
                                title="閉じる（Esc）"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>閉じる</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* コンテンツ */}
                        <div className="p-4">
                            <MathEditor
                                value={currentMathValue}
                                onChange={setCurrentMathValue}
                                onComplete={() => handleMathComplete(currentMathValue)}
                                onCancel={handleMathCancel}
                                isVisible={true}
                            />

                            <div className="mt-4 pt-4 border-t border-gray-200">
                                <p className="text-xs text-gray-500">
                                    <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs font-mono">Enter</kbd> 確定 /
                                    <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs font-mono ml-2">Esc</kbd> キャンセル
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* ヘッダー */}
                <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-200">
                    <h3 className="text-sm font-semibold text-gray-800">数学テキスト入力</h3>
                </div>

                {/* メイン */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 min-h-0 min-w-0">
                    <div className="lg:col-span-2 flex flex-col space-y-3 min-h-0 min-w-0">
                        {/* 表示モード切り替え */}
                        <div className="flex gap-1 bg-gray-100 p-1 rounded">
                            <button
                                type="button"
                                onClick={() => setViewMode('edit')}
                                disabled={isGenerating}
                                className={`px-3 py-2 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${viewMode === 'edit' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>編集</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                編集のみ
                            </button>
                            <button
                                type="button"
                                onClick={() => setViewMode('split')}
                                disabled={isGenerating || !text.trim()}
                                className={`px-3 py-2 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${viewMode === 'split' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>分割</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
                                </svg>
                                編集+プレビュー
                            </button>
                            <button
                                type="button"
                                onClick={() => setViewMode('preview')}
                                disabled={isGenerating || !text.trim()}
                                className={`px-3 py-2 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${viewMode === 'preview' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>プレビュー</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                                プレビューのみ
                            </button>
                        </div>

                        {/* ツールバー */}
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={loadSampleText}
                                disabled={isGenerating}
                                className="px-3 py-2 text-xs font-medium bg-white text-gray-700 border border-gray-300 rounded hover:bg-gray-50 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>サンプル</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                サンプルを読み込む
                            </button>
                            <button
                                type="button"
                                onClick={handleMathEditorOpen}
                                disabled={isGenerating || viewMode === 'preview'}
                                className="px-3 py-2 text-xs font-medium bg-white text-gray-700 border border-gray-300 rounded hover:bg-gray-50 hover:border-gray-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                                title={viewMode === 'preview' ? 'プレビューモードでは使用できません' : '数式を挿入'}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <title>数式</title>
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                数式を挿入
                            </button>
                        </div>

                        {/* メインエディタエリア */}
                        <div className="flex-1 min-h-0">
                            {viewMode === 'edit' && (
                                <textarea
                                    ref={textAreaRef}
                                    id="math-text"
                                    value={text}
                                    onChange={handleTextAreaChange}
                                    onClick={handleTextAreaClick}
                                    onKeyDown={handleTextAreaKeyDown}
                                    placeholder={placeholderText}
                                    className="w-full h-full p-4 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm resize-none"
                                    disabled={isGenerating}
                                />
                            )}

                            {viewMode === 'preview' && <PreviewPanel text={text} className="h-full" />}

                            {viewMode === 'split' && (
                                <div className="flex gap-3 h-full">
                                    <div className="flex-1">
                                        <textarea
                                            id="math-text-split"
                                            ref={textAreaRef}
                                            value={text}
                                            onChange={handleTextAreaChange}
                                            onClick={handleTextAreaClick}
                                            onKeyDown={handleTextAreaKeyDown}
                                            placeholder={placeholderText}
                                            className="w-full h-full p-4 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm resize-none"
                                            disabled={isGenerating}
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <PreviewPanel text={text} className="h-full" />
                                    </div>
                                </div>
                            )}
                        </div>

                        <p className="text-xs text-gray-500">
                            {viewMode === 'split' ? (
                                <>左側で編集すると右側にリアルタイムでプレビューが表示されます</>
                            ) : viewMode === 'preview' ? (
                                <>数式とMarkdownのレンダリング結果</>
                            ) : (
                                <>数式は $...$ または $$...$$ で囲んでください</>
                            )}
                        </p>
                    </div>

                    {/* 右側: 操作エリア */}
                    <div className="flex flex-col min-h-0 min-w-0">
                        <div className="overflow-y-auto flex-1 min-h-0 pr-2">
                            <div className="space-y-3">
                                {/* AIで文章のひな形を生成 */}
                                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                                    <h5 className="text-sm font-medium text-gray-800 mb-2 flex items-center gap-2">
                                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <title>AI</title>
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                        </svg>
                                        AIで文章のひな形を生成
                                    </h5>
                                    <div className="flex flex-col gap-2">
                                        <input
                                            type="text"
                                            value={titleInput}
                                            onChange={(e) => setTitleInput(e.target.value)}
                                            placeholder="例: 積分の方法、微分の公式"
                                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            disabled={isGeneratingContent || isGenerating}
                                        />
                                        <button
                                            type="button"
                                            onClick={handleGenerateFromTitle}
                                            disabled={!titleInput.trim() || isGeneratingContent || isGenerating}
                                            className="w-full px-4 py-2 text-sm font-medium text-white bg-gray-700 rounded hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                                        >
                                            {isGeneratingContent ? '生成中...' : '生成'}
                                        </button>
                                    </div>
                                    {generationError && <p className="mt-2 text-xs text-red-600">{generationError}</p>}
                                    <p className="mt-2 text-xs text-gray-600">トピックのタイトルを入力すると、Markdown + LaTeX形式の解説を生成します</p>
                                </div>

                                {/* 動画への追加指示 */}
                                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                                    <h5 className="text-sm font-medium text-gray-800 mb-2 flex items-center gap-2">
                                        <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <title>動画</title>
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                        </svg>
                                        動画への追加指示（任意）
                                    </h5>
                                    <textarea
                                        id="video-prompt"
                                        value={videoPrompt}
                                        onChange={(e) => setVideoPrompt(e.target.value)}
                                        placeholder="例: 積分記号を赤色で強調、文字サイズを大きく"
                                        className="w-full p-3 text-sm border border-gray-300 rounded h-24 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                        disabled={isGenerating}
                                    />
                                    <p className="mt-1 text-xs text-gray-500">動画の見た目や演出について具体的に指示できます</p>
                                </div>

                                {/* プロンプト生成ボタン */}
                                <div className="pt-3 border-t border-gray-200">
                                    <button
                                        type="submit"
                                        disabled={!text.trim() || isGenerating}
                                        className="w-full bg-blue-600 text-white py-4 px-6 rounded text-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm flex items-center justify-center gap-2"
                                    >
                                        {isGenerating ? (
                                            <>
                                                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                                    <title>生成中</title>
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                    <path
                                                        className="opacity-75"
                                                        fill="currentColor"
                                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                                    />
                                                </svg>
                                                プロンプト生成中...
                                            </>
                                        ) : (
                                            <>
                                                プロンプトを生成して次へ
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <title>次へ</title>
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                                </svg>
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        </ErrorProvider>
    )
}
