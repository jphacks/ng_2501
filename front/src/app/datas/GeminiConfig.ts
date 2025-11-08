// Domain層: Gemini API設定とデータモデル

export const DEFAULT_MODEL = 'gemini-2.5-flash-lite';
export const AUTOCOMPLETE_MAX_OUTPUT_TOKENS = 512;
export const COMPLETION_MAX_OUTPUT_TOKENS = 2048;

export interface GeminiMathContinuationResult {
    completions: string[];
}

export interface GeminiCompletionResult {
    content: string;
}

export class GeminiError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'GeminiError';
    }
}

// Gemini API設定の取得
export const getGeminiModel = (): string => {
    const envModel = process.env.NEXT_PUBLIC_GEMINI_MODEL;
    return typeof envModel === 'string' && envModel.trim() ? envModel.trim() : DEFAULT_MODEL;
};

export const getGeminiApiKey = (): string | null => {
    const apiKey = process.env.NEXT_PUBLIC_GEMINI_API_KEY;
    return typeof apiKey === 'string' && apiKey.trim() ? apiKey.trim() : null;
};

// プロンプト生成: 数式補完
export const buildMathContinuationPrompt = (latex: string): string => {
    return [
        'You assist with editing LaTeX math expressions in a note-taking app.',
        'The user is a high school student. Your suggestions should be appropriate for a high school mathematics curriculum (e.g., algebra, geometry, trigonometry, and basic calculus).',
        'Rules:',
        '1. Provide one or two candidate expressions, placing each candidate on its own line.',
        '2. **Crucially, ensure all suggestions are mathematically correct.** Do not provide deliberately incorrect or nonsensical options.',
        "3. **If the user's expression is already a complete and correct mathematical statement (e.g., an identity like `(x+2)^2 = x^2 + 4x + 4`), do not provide any suggestions. In this case, return an empty response.**",
        '4. Return complete LaTeX expressions that can replace the current expression. Include the original left-hand side when extending an equation.',
        '5. If the current expression contains \\placeholder{} or \\mathplaceholder{} tokens, replace every placeholder with a sensible mathematical value—never leave placeholder tokens in your output.',
        '6. When no placeholders are present, continue the expression naturally (e.g., finish the right-hand side after an equals sign, simplify, or evaluate).',
        '7. Output LaTeX only: no prose, numbering, bullet markers, or surrounding $...$ / $$...$$ delimiters.',
        '8. Keep each candidate concise (ideally under 60 tokens).',
        `Current expression:\n${latex}`,
    ].join('\n');
};

// プロンプト生成: タイトルから数学ノート生成
export const buildCompletionPrompt = (title: string): string => {
  return [
    '高校数学のテーマから説明するためのアニメーションを考えてください。',
    `理解を助ける具体的手順を120〜150字の一文で書いてください。`,
    '高校数学の用語を使って、解説をしてください。',
    '出力は一文のみ・前置きや箇条書き禁止・必ず「〜してください」で終えてください。',
    `テーマ: ${title}`,
  ].join('\n');
};