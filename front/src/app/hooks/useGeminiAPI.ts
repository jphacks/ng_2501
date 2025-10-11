// UseCase層: Gemini API呼び出しロジック

import {
    AUTOCOMPLETE_MAX_OUTPUT_TOKENS,
    GeminiError,
    type GeminiMathContinuationResult,
    buildMathContinuationPrompt,
    getGeminiApiKey,
    getGeminiModel,
} from '../datas/GeminiConfig';

/**
 * Gemini APIを使用して数式の補完候補を取得
 */
export const predictMathContinuation = async (
    latex: string,
    signal?: AbortSignal
): Promise<GeminiMathContinuationResult> => {
    const apiKey = getGeminiApiKey();

    if (!apiKey) {
        throw new GeminiError('Gemini API key is not configured.');
    }

    const model = getGeminiModel();
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
    const prompt = buildMathContinuationPrompt(latex);

    const requestBody = {
        contents: [
            {
                role: 'user',
                parts: [
                    {
                        text: prompt,
                    },
                ],
            },
        ],
        generationConfig: {
            temperature: 0.3,
            topP: 0.95,
            topK: 40,
            maxOutputTokens: AUTOCOMPLETE_MAX_OUTPUT_TOKENS,
        },
    };

    let response: Response;

    try {
        response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
            signal,
        });
    } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
            throw error;
        }
        throw new GeminiError('Failed to reach Gemini API.');
    }

    if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        throw new GeminiError(
            `Gemini API request failed (${response.status}): ${errorText || response.statusText}`
        );
    }

    const data = await response.json();
    const firstCandidate = data?.candidates?.[0];
    const parts = firstCandidate?.content?.parts;
    const text =
        Array.isArray(parts) && parts.length > 0
            ? parts
                .map((part: { text?: string }) => (typeof part.text === 'string' ? part.text : ''))
                .join('\n')
                .trim()
            : '';

    if (typeof text !== 'string') {
        throw new GeminiError('Gemini API did not return any content.');
    }

    if (!text) {
        return { completions: [] };
    }

    const suggestions = text
        .split('\n')
        .map((line: string) => line.trim())
        .filter((line: string) => line.length > 0)
        .slice(0, 2);

    return { completions: suggestions };
};

