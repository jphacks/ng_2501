// Domain層: 動画生成のデータ形式とバリデーション

/**
 * 動画生成リクエスト
 * ユーザーが入力するテキストと動画プロンプト
 */
export interface VideoGenerationRequest {
    text: string // 数式を含むテキスト（LaTeX形式対応）
    videoPrompt?: string // 動画のプロンプト（任意）
}

/**
 * 動画生成用プロンプト
 * AIが生成した中間プロンプト
 */
export interface VideoGenerationPrompt {
    prompt: string // 編集可能なプロンプト
    manimCode?: string // manim原文（トグルで表示）
    originalText: string // 原文
}

/**
 * 動画生成結果
 */
export interface VideoResult {
    videoId: string // 生成された動画ID
    videoUrl: string // 生成された動画のURL
    prompt: VideoGenerationPrompt // 使用されたプロンプト
    generatedAt: Date // 生成日時
}

/**
 * 動画編集リクエスト
 * 生成された動画に対する追加の指示
 */
export interface VideoEditRequest {
    videoId: string // 編集対象の動画ID
    editPrompt: string // 編集内容の指示
}

/**
 * 動画生成リクエストのバリデーション
 */
export function validateVideoGeneration(request: VideoGenerationRequest): {
    isValid: boolean
    errors: string[]
} {
    const errors: string[] = []

    if (!request.text || request.text.trim().length === 0) {
        errors.push('テキストは必須です')
    }

    if (request.text && request.text.length < 10) {
        errors.push('テキストは10文字以上必要です')
    }

    return {
        isValid: errors.length === 0,
        errors,
    }
}

/**
 * 動画編集リクエストのバリデーション
 */
export function validateVideoEdit(request: VideoEditRequest): {
    isValid: boolean
    errors: string[]
} {
    const errors: string[] = []

    if (!request.videoId || request.videoId.trim().length === 0) {
        errors.push('動画IDは必須です')
    }

    if (!request.editPrompt || request.editPrompt.trim().length === 0) {
        errors.push('編集内容の指示は必須です')
    }

    return {
        isValid: errors.length === 0,
        errors,
    }
}

/**
 * バリデーションエラー
 */
export class ValidationError extends Error {
    constructor(public errors: string[]) {
        super(errors.join(', '))
        this.name = 'ValidationError'
    }
}
