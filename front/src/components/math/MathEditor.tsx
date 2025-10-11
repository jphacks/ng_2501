'use client'

import React, { useCallback, useEffect, useMemo } from 'react';
import katex from 'katex';
import { LazyMathField } from './LazyMathField';
import type { MathFieldRef } from './MathField';
import { useMathField } from '@/app/hooks/useMathField';
import { useTouchDevice } from '@/app/hooks/useTouchDevice';
import { useMathAutocomplete } from '@/app/hooks/useMathAutocomplete';

const PLACEHOLDER_WITH_BRACES_REGEX = /\\(?:math)?placeholder(?:\[[^\]]*])?{[^{}]*}/;
const PLACEHOLDER_WITH_BRACES_GLOBAL_REGEX = /\\(?:math)?placeholder(?:\[[^\]]*])?{[^{}]*}/g;
const BARE_PLACEHOLDER_REGEX = /\\(?:math)?placeholder\b/;
const BARE_PLACEHOLDER_GLOBAL_REGEX = /\\(?:math)?placeholder\b/g;
const PLACEHOLDER_SEPARATOR_REGEX = /\s*[;|]\s*/;

// MathEditor component props
export interface MathEditorProps {
    value?: string;
    onChange?: (latex: string) => void;
    onComplete?: () => void;
    onCancel?: () => void;
    isVisible?: boolean;
    className?: string;
    style?: React.CSSProperties;
    suggestionDebounceMs?: number;
}

interface PlaceholderMatchInfo {
    index: number;
    length: number;
}

const stripPlaceholderTokens = (latex: string): string => {
    PLACEHOLDER_WITH_BRACES_GLOBAL_REGEX.lastIndex = 0;
    BARE_PLACEHOLDER_GLOBAL_REGEX.lastIndex = 0;

    return latex
        .replace(PLACEHOLDER_WITH_BRACES_GLOBAL_REGEX, '')
        .replace(BARE_PLACEHOLDER_GLOBAL_REGEX, '')
        .trim();
};

const findNextPlaceholder = (latex: string): PlaceholderMatchInfo | null => {
    PLACEHOLDER_WITH_BRACES_REGEX.lastIndex = 0;
    const withBraces = PLACEHOLDER_WITH_BRACES_REGEX.exec(latex);
    if (withBraces && typeof withBraces.index === 'number') {
        return { index: withBraces.index, length: withBraces[0].length };
    }

    BARE_PLACEHOLDER_REGEX.lastIndex = 0;
    const bare = BARE_PLACEHOLDER_REGEX.exec(latex);
    if (bare && typeof bare.index === 'number') {
        return { index: bare.index, length: bare[0].length };
    }

    return null;
};

const countPlaceholders = (latex: string): number => {
    if (!latex) {
        return 0;
    }

    let count = 0;
    let remaining = latex;

    while (true) {
        const match = findNextPlaceholder(remaining);
        if (!match) {
            break;
        }

        count += 1;
        remaining = remaining.slice(match.index + match.length);
    }

    return count;
};

const fillPlaceholdersFromSuggestion = (
    baseLatex: string,
    suggestionLatex: string
): { changed: boolean; result: string } => {
    const placeholderCount = countPlaceholders(baseLatex);
    if (!placeholderCount) {
        return { changed: false, result: baseLatex };
    }

    const trimmedSuggestion = suggestionLatex.trim();
    if (!trimmedSuggestion) {
        return { changed: false, result: baseLatex };
    }

    const looksLikeFullExpression =
        /=/.test(trimmedSuggestion) ||
        trimmedSuggestion.includes('\\int') ||
        trimmedSuggestion.includes('\\sum') ||
        trimmedSuggestion.includes('\\prod') ||
        trimmedSuggestion.includes('\\begin');

    if (looksLikeFullExpression) {
        return { changed: false, result: baseLatex };
    }

    const needsMultiple = placeholderCount > 1 && PLACEHOLDER_SEPARATOR_REGEX.test(trimmedSuggestion);
    const segments = needsMultiple
        ? trimmedSuggestion.split(PLACEHOLDER_SEPARATOR_REGEX).filter(Boolean)
        : [trimmedSuggestion];

    const values: string[] = [];
    if (segments.length === 1 && placeholderCount > 1) {
        for (let i = 0; i < placeholderCount; i += 1) {
            values.push(segments[0]);
        }
    } else {
        values.push(...segments.slice(0, placeholderCount));
    }

    let updatedLatex = baseLatex;
    let replacedAny = false;

    for (const rawValue of values) {
        const match = findNextPlaceholder(updatedLatex);
        if (!match) {
            break;
        }

        const before = updatedLatex.slice(0, match.index);
        const after = updatedLatex.slice(match.index + match.length);
        const trimmedValue = rawValue.trim();
        if (!trimmedValue) {
            continue;
        }

        const charBefore = before.trimEnd().slice(-1);
        let insertion = trimmedValue;
        if ((charBefore === '_' || charBefore === '^') && !(insertion.startsWith('{') && insertion.endsWith('}'))) {
            insertion = `{${insertion}}`;
        }

        updatedLatex = `${before}${insertion}${after}`;
        replacedAny = true;
    }

    return { changed: replacedAny, result: updatedLatex };
};

const relationalSuffixRegex = /(=|≈|≃|≅|≤|≥|<|>)\s*$/;
const relationalPrefixRegex = /^\s*=|^\\(?:approx|sim|equiv|leftrightarrow|iff|implies|rightarrow|Rightarrow|to|mapsto)\b/;

const appendAfterRelational = (base: string, addition: string): string => {
    if (relationalSuffixRegex.test(base)) {
        const cleanedAddition = addition.replace(/^\s*=+\s*/, '').trimStart();
        return cleanedAddition ? `${base} ${cleanedAddition}` : base;
    }

    return `${base} ${addition}`;
};

const formatForPreview = (latex: string): string => {
    PLACEHOLDER_WITH_BRACES_GLOBAL_REGEX.lastIndex = 0;
    BARE_PLACEHOLDER_GLOBAL_REGEX.lastIndex = 0;

    const replaced = latex
        .replace(PLACEHOLDER_WITH_BRACES_GLOBAL_REGEX, '\\square')
        .replace(BARE_PLACEHOLDER_GLOBAL_REGEX, '\\square');

    return replaced;
};

/**
 * MathEditor component - Provides a user-friendly interface for math input
 * Uses MathLive for rich mathematical expression editing
 */
export const MathEditor: React.FC<MathEditorProps> = ({
    value = '',
    onChange,
    onComplete,
    onCancel,
    isVisible = true,
    className = '',
    style,
    suggestionDebounceMs = 500
}) => {
    const { deviceInfo } = useTouchDevice();

    const {
        mathFieldRef,
        value: mathValue,
        setValue,
        focus,
        blur,
        isActive,
        setIsActive
    } = useMathField({
        initialValue: value,
        virtualKeyboardMode: deviceInfo.isTouch && !deviceInfo.hasPhysicalKeyboard ? 'onfocus' : 'manual',
        smartMode: true
    });

    const {
        suggestions,
        isLoading: isSuggestionLoading,
        error: suggestionError,
        clearSuggestions,
    } = useMathAutocomplete({
        latex: mathValue,
        isActive,
        debounceMs: suggestionDebounceMs
    });

    const combineWithBaseLatex = useCallback(
        (suggestionLatex: string): string => {
            const baseValue = mathValue;
            const baseTrimmed = baseValue.trim();
            const suggestionTrimmed = suggestionLatex.trim();

            if (!suggestionTrimmed) {
                return baseValue;
            }

            const { changed, result: placeholderFilled } = fillPlaceholdersFromSuggestion(
                baseValue,
                suggestionTrimmed
            );
            if (changed) {
                return placeholderFilled;
            }

            if (!baseTrimmed) {
                return stripPlaceholderTokens(suggestionTrimmed);
            }

            if (suggestionTrimmed.startsWith(baseTrimmed)) {
                return stripPlaceholderTokens(suggestionTrimmed);
            }

            if (relationalSuffixRegex.test(baseTrimmed) || relationalPrefixRegex.test(suggestionTrimmed)) {
                return appendAfterRelational(baseTrimmed, suggestionTrimmed);
            }

            if (
                /=/.test(suggestionTrimmed) ||
                suggestionTrimmed.includes('\\int') ||
                suggestionTrimmed.includes('\\sum') ||
                suggestionTrimmed.includes('\\prod')
            ) {
                return stripPlaceholderTokens(suggestionTrimmed);
            }

            return `${baseTrimmed} ${suggestionTrimmed}`;
        },
        [mathValue]
    );

    const renderSuggestionPreview = useCallback(
        (suggestionLatex: string): string | null => {
            const combined = combineWithBaseLatex(suggestionLatex);
            if (!combined) {
                return null;
            }

            const formatted = formatForPreview(combined).trim();
            const previewLatex = formatted.length > 0 ? formatted : '\\square';

            try {
                return katex.renderToString(previewLatex, {
                    throwOnError: false,
                    displayMode: false,
                });
            } catch (error) {
                return null;
            }
        },
        [combineWithBaseLatex]
    );

    // Update internal value when prop changes
    useEffect(() => {
        if (value !== mathValue) {
            setValue(value);
        }
    }, [value, mathValue, setValue]);

    // Handle value changes
    const handleChange = (latex: string) => {
        setValue(latex);
        onChange?.(latex);
    };

    // Handle focus
    const handleFocus = () => {
        setIsActive(true);
    };

    // Handle blur
    const handleBlur = () => {
        setIsActive(false);
        clearSuggestions();
    };

    // Handle completion (Enter key)
    const handleComplete = () => {
        onComplete?.();
        blur();
    };

    // Handle cancellation (Escape key)
    const handleCancel = () => {
        onCancel?.();
        blur();
        clearSuggestions();
    };

    // Auto-focus when visible
    useEffect(() => {
        if (isVisible) {
            // Use requestAnimationFrame to ensure DOM is ready, then add a small delay
            requestAnimationFrame(() => {
                setTimeout(() => {
                    if (mathFieldRef.current) {
                        focus();
                        // For touch devices, ensure virtual keyboard appears
                        if (deviceInfo.isTouch) {
                            // Additional focus attempt for touch devices
                            focus();
                        }
                    }
                }, 150); // Slightly longer delay for better reliability
            });
        }
    }, [isVisible, focus, deviceInfo.isTouch, mathFieldRef]);

    const handleSuggestionSelect = useCallback(
        (continuation: string) => {
            if (!continuation) {
                return;
            }

            const nextValue = combineWithBaseLatex(continuation);
            if (nextValue === null || nextValue === undefined) {
                clearSuggestions();
                return;
            }

            setValue(nextValue);
            onChange?.(nextValue);

            // Directly update the MathField element's value.
            if (mathFieldRef.current) {
                try {
                    mathFieldRef.current.setValue(nextValue);
                } catch (error) {
                    console.error('Failed to apply suggestion to MathField', error);
                }
            }

            clearSuggestions();

            requestAnimationFrame(() => {
                focus();
            });
        },
        [combineWithBaseLatex, setValue, onChange, clearSuggestions, focus, mathFieldRef]
    );

    const showSuggestionPanel = useMemo(
        () =>
            suggestions.length > 0 || Boolean(suggestionError) || isSuggestionLoading,
        [suggestions, suggestionError, isSuggestionLoading]
    );

    const preventMouseDown = (e: React.MouseEvent) => {
        e.preventDefault();
    };

    if (!isVisible) {
        return null;
    }

    // Touch optimization is handled in the MathField component

    return (
        <div
            className={`math-editor ${className} ${isActive ? 'active' : ''} ${deviceInfo.isTouch ? 'touch-optimized' : ''
                } ${deviceInfo.isMobile ? 'mobile-optimized' : ''}`}
            style={style}
        >
            <div className="math-editor-field">
                <LazyMathField
                    ref={mathFieldRef as unknown as React.Ref<MathFieldRef>}
                    value={mathValue}
                    onChange={handleChange}
                    onFocus={handleFocus}
                    onBlur={handleBlur}
                    onComplete={handleComplete}
                    className="math-field"
                />

                {showSuggestionPanel && (
                    <div className="math-editor-suggestions">
                        {isSuggestionLoading && (
                            <span className="math-editor-suggestion-status">Calculating suggestions...</span>
                        )}
                        {!isSuggestionLoading && suggestionError && (
                            <span className="math-editor-suggestion-error">{suggestionError}</span>
                        )}
                        {!isSuggestionLoading && !suggestionError && suggestions.length > 0 && (
                            <>
                                <span className="math-editor-suggestion-label">Suggestions</span>
                                <div className="math-editor-suggestion-list" role="list">
                                    {suggestions.map((option, index) => {
                                        const previewHtml = renderSuggestionPreview(option);
                                        const fallback = combineWithBaseLatex(option);

                                        return (
                                            <button
                                                key={`${option}-${index}`}
                                                type="button"
                                                role="listitem"
                                                className="math-editor-suggestion-item"
                                                onClick={() => handleSuggestionSelect(option)}
                                                onMouseDown={preventMouseDown}
                                                aria-label={`Suggestion ${index + 1}`}
                                            >
                                                {previewHtml ? (
                                                    <span
                                                        className="math-editor-suggestion-preview"
                                                        dangerouslySetInnerHTML={{ __html: previewHtml }}
                                                    />
                                                ) : (
                                                    <span className="math-editor-suggestion-fallback">
                                                        {fallback || option}
                                                    </span>
                                                )}
                                            </button>
                                        );
                                    })}
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>

            <div className="math-editor-controls">
                <button
                    type="button"
                    onClick={handleComplete}
                    className="math-editor-btn math-editor-btn-complete"
                    title="Complete (Enter)"
                    aria-label="Complete math input"
                >
                    ✓
                </button>
                <button
                    type="button"
                    onClick={handleCancel}
                    className="math-editor-btn math-editor-btn-cancel"
                    title="Cancel (Escape)"
                    aria-label="Cancel math input"
                >
                    ✕
                </button>
            </div>
        </div>
    );
};


