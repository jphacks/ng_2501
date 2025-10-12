import { useCallback, useEffect, useRef, useState } from 'react';
import { GeminiError } from '@/app/datas/GeminiConfig';
import { predictMathContinuation } from '@/app/hooks/useGeminiAPI';
import { validateLatex } from '@/app/datas/MathValidation';

const PLACEHOLDER_TOKEN_REGEX = /\\(?:math)?placeholder(?:\[[^\]]*])?{[^{}]*}/g;
const BARE_PLACEHOLDER_REGEX = /\\(?:math)?placeholder\b/g;

export interface MathAutocompleteOptions {
    latex: string;
    isActive: boolean;
    debounceMs?: number;
}

export interface MathAutocompleteState {
    suggestions: string[];
    isLoading: boolean;
    error: string | null;
    clearSuggestions: () => void;
}

const sanitizeContinuation = (continuation: string, currentLatex: string): string => {
    if (!continuation) return '';

    let normalized = continuation.replace(/\r/g, '').trim();

    normalized = normalized
        .replace(/^(?:\d+[\.)]|[-•])\s*/, '')
        .replace(/^option\s*\d+\s*[:\-]?\s*/i, '');

    if (!normalized) {
        return '';
    }

    // Remove leading/trailing math delimiters that are not part of the continuation.
    normalized = normalized.replace(/^\${1,2}/, '').replace(/\${1,2}$/, '').trim();

    normalized = normalized.replace(PLACEHOLDER_TOKEN_REGEX, '').trim();
    normalized = normalized.replace(BARE_PLACEHOLDER_REGEX, '').trim();

    // Avoid echoing the current latex; some responses may return the full expression.
    if (normalized.startsWith(currentLatex.trim())) {
        normalized = normalized.slice(currentLatex.trim().length).trimStart();
    }

    // Guard against pathological outputs (long paragraphs, markdown)
    if (normalized.includes('\n\n') || normalized.length > 400) {
        return '';
    }

    return normalized;
};

export const useMathAutocomplete = ({
    latex,
    isActive,
    debounceMs = 500,
}: MathAutocompleteOptions): MathAutocompleteState => {
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const latestRequestRef = useRef(0);
    const abortControllerRef = useRef<AbortController | null>(null);

    const clearSuggestions = useCallback(() => {
        setSuggestions([]);
        setError(null);
        abortControllerRef.current?.abort();
        abortControllerRef.current = null;
    }, []);

    useEffect(() => {
        if (!isActive) {
            clearSuggestions();
            setIsLoading(false);
            return;
        }

        const trimmedLatex = latex.trim();
        if (!trimmedLatex || trimmedLatex.length < 4) {
            clearSuggestions();
            setIsLoading(false);
            return;
        }

        const requestId = latestRequestRef.current + 1;
        latestRequestRef.current = requestId;

        abortControllerRef.current?.abort();
        const controller = new AbortController();
        abortControllerRef.current = controller;

        const timer = window.setTimeout(async () => {
            setIsLoading(true);
            setError(null);

            try {
                const { completions } = await predictMathContinuation(trimmedLatex, controller.signal);

                if (latestRequestRef.current !== requestId) {
                    return;
                }

                const normalized = (Array.isArray(completions) ? completions : [completions])
                    .map((item) => sanitizeContinuation(item, trimmedLatex))
                    .filter((item) => {
                        if (item.length === 0) return false;
                        const validation = validateLatex(item);
                        return validation.isValid;
                    });

                const unique = normalized.filter((item, index, array) => array.indexOf(item) === index);

                setSuggestions(unique.slice(0, 2));
            } catch (err) {
                if (err instanceof DOMException && err.name === 'AbortError') {
                    return;
                }

                if (err instanceof GeminiError) {
                    setError(err.message);
                } else {
                    setError('Failed to get suggestions.');
                }
                setSuggestions([]);
            } finally {
                if (latestRequestRef.current === requestId) {
                    setIsLoading(false);
                }
            }
        }, debounceMs);

        return () => {
            window.clearTimeout(timer);
            if (abortControllerRef.current && latestRequestRef.current !== requestId) {
                abortControllerRef.current.abort();
            }
        };
    }, [latex, isActive, debounceMs, clearSuggestions]);

    useEffect(
        () => () => {
            abortControllerRef.current?.abort();
        },
        []
    );

    return {
        suggestions,
        isLoading,
        error,
        clearSuggestions,
    };
};


