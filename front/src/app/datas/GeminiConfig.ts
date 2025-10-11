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
    const hasJapanese = /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]/.test(title);
    const targetLanguage = hasJapanese ? 'Japanese' : 'English';

    return [
        `You are preparing structured math-learning content titled "${title}".`,
        `Respond in ${targetLanguage}.`,
        'Produce concise markdown with exactly 3 sections.',
        'Each section must:',
        '1. Start with a level-2 heading (##).',
        '2. Reuse and analyze a single primary LaTeX equation; show the full equation once and refer to its components or rearrangements rather than introducing unrelated formulas.',
        'Ensure each section includes at least one LaTeX expression derived from that primary equation (inline $...$ or block $$...$$).',
        '3. Focus purely on mathematical definitions, symbolic manipulation, and planar (2D) interpretations that can be readily visualized; avoid 3D topics.',
        'Keep prose minimal—prioritize the equation, its derivation, term-by-term explanations, and a short worked numeric example when possible.',
        'End the final section with a bullet list titled "Tips" that briefly notes at least one real-world or computational use case of the equation.',
        'Limit the entire response to roughly 1,000 characters; stay concise while fulfilling the requirements.',
        'Do not modify or restate the provided title, and avoid adding placeholder text or unrelated English filler.',
    ].join('\n');
};

