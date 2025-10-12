'use client'

import React, {
    useEffect,
    useRef,
    useImperativeHandle,
    forwardRef,
    useState,
} from "react";
import type { MathfieldElement } from "mathlive";
import { initializeMathLive, validateLatex } from "@/utils/mathLiveUtils";
import { useMathError } from "@/app/contexts/ErrorContext";
import { MathRenderError } from "@/app/datas/MathError";
import { useTouchDevice } from "@/app/hooks/useTouchDevice";

// Extend MathfieldElement interface to include missing properties
declare module "mathlive" {
    interface MathfieldElement {
        virtualKeyboardMode: "manual" | "onfocus" | "off";
        virtualKeyboardPolicy: "auto" | "manual" | "sandboxed";
        virtualKeyboardTheme: "apple" | "material" | "";
        keypressVibration: boolean;
        smartMode: boolean;
        readOnly: boolean;
    }
}

// MathField component props interface
export interface MathFieldProps {
    value?: string;
    onChange?: (latex: string) => void;
    onFocus?: () => void;
    onBlur?: () => void;
    onComplete?: () => void;
    className?: string;
    style?: React.CSSProperties;
    virtualKeyboardMode?: "manual" | "onfocus" | "off";
    smartMode?: boolean;
    readOnly?: boolean;
}

// MathField component ref interface
export interface MathFieldRef {
    getValue: () => string;
    setValue: (value: string) => void;
    focus: () => void;
    blur: () => void;
    insert: (latex: string) => void;
    clear: () => void;
}

// MathField component - React wrapper for MathfieldElement
export const MathField = forwardRef<MathFieldRef, MathFieldProps>(
    (
        {
            value = "",
            onChange,
            onFocus,
            onBlur,
            onComplete,
            className = "",
            style,
            virtualKeyboardMode = "manual",
            smartMode = true,
            readOnly = false,
        },
        ref
    ) => {
        const mathfieldRef = useRef<MathfieldElement>(null);
        const [isInitialized, setIsInitialized] = useState(false);
        const [initError, setInitError] = useState<string | null>(null);
        const { handleMathError } = useMathError();
        const { deviceInfo } = useTouchDevice();

        // Initialize MathLive
        useEffect(() => {
            let mounted = true;

            const initialize = async () => {
                try {
                    // Dynamically import MathLive to ensure it loads in the browser
                    if (typeof window !== 'undefined') {
                        await import('mathlive');
                    }
                    
                    if (!mounted) return;

                    // Wait a bit for custom elements to register
                    await new Promise(resolve => setTimeout(resolve, 100));
                    
                    const loaded = await initializeMathLive();
                    if (!mounted) return;

                    if (!loaded) {
                        const error = new MathRenderError(
                            "Failed to load MathLive library",
                            ""
                        );
                        handleMathError(error);
                        setInitError("MathLive failed to load");
                        return;
                    }

                    setIsInitialized(true);
                    setInitError(null);
                } catch (error) {
                    if (!mounted) return;
                    const mathError = new MathRenderError(
                        "Error initializing MathLive",
                        "",
                        error instanceof Error ? error : new Error(String(error))
                    );
                    handleMathError(mathError);
                    setInitError("Failed to initialize MathLive");
                }
            };

            initialize();

            return () => {
                mounted = false;
            };
        }, [handleMathError]);

        // Configure MathfieldElement after initialization
        useEffect(() => {
            const mathfield = mathfieldRef.current;
            if (!mathfield || !isInitialized) return;

            try {
                // Configure MathLive settings using properties with touch optimizations
                const optimalVirtualKeyboardMode =
                    deviceInfo.isTouch && !deviceInfo.hasPhysicalKeyboard
                        ? "onfocus"
                        : virtualKeyboardMode;

                mathfield.virtualKeyboardMode = optimalVirtualKeyboardMode;
                mathfield.smartMode = smartMode;
                mathfield.readOnly = readOnly;

                // Touch-specific optimizations
                if (deviceInfo.isTouch) {
                    // Enable virtual keyboard for touch devices
                    mathfield.virtualKeyboardPolicy = "auto";

                    // Optimize for mobile devices
                    if (deviceInfo.isMobile) {
                        mathfield.virtualKeyboardTheme = "material";
                        mathfield.keypressVibration = true;
                    }
                }

                // Set inline shortcuts
                mathfield.inlineShortcuts = {
                    alpha: "\\alpha",
                    beta: "\\beta",
                    gamma: "\\gamma",
                    delta: "\\delta",
                    epsilon: "\\epsilon",
                    theta: "\\theta",
                    lambda: "\\lambda",
                    mu: "\\mu",
                    pi: "\\pi",
                    sigma: "\\sigma",
                    phi: "\\phi",
                    omega: "\\omega",
                    sum: "\\sum",
                    int: "\\int",
                    frac: "\\frac{#@}{#?}",
                    sqrt: "\\sqrt{#@}",
                    lim: "\\lim_{#@}",
                    infty: "\\infty",
                    partial: "\\partial",
                    nabla: "\\nabla",
                };
            } catch (error) {
                const mathError = new MathRenderError(
                    "Error configuring MathField",
                    "",
                    error instanceof Error ? error : new Error(String(error))
                );
                handleMathError(mathError);
            }

            // Set initial value
            if (value) {
                try {
                    const validation = validateLatex(value);
                    if (!validation.isValid) {
                        const mathError = new MathRenderError(
                            `Invalid LaTeX: ${validation.error}`,
                            value
                        );
                        handleMathError(mathError);
                    } else {
                        mathfield.value = value;
                    }
                } catch (error) {
                    const mathError = new MathRenderError(
                        "Error setting initial value",
                        value,
                        error instanceof Error ? error : new Error(String(error))
                    );
                    handleMathError(mathError);
                }
            }

            // Event listeners
            const handleInput = () => {
                try {
                    const latex = mathfield.value;
                    const validation = validateLatex(latex);
                    if (!validation.isValid && latex.trim()) {
                        const mathError = new MathRenderError(
                            `Invalid LaTeX: ${validation.error}`,
                            latex
                        );
                        handleMathError(mathError);
                    }
                    onChange?.(latex);
                } catch (error) {
                    const mathError = new MathRenderError(
                        "Error handling input",
                        "",
                        error instanceof Error ? error : new Error(String(error))
                    );
                    handleMathError(mathError);
                }
            };

            const handleFocus = () => {
                try {
                    onFocus?.();
                } catch (error) {
                    console.error("Error handling focus:", error);
                }
            };

            const handleBlur = () => {
                try {
                    onBlur?.();
                } catch (error) {
                    console.error("Error handling blur:", error);
                }
            };

            const handleKeydown = (event: KeyboardEvent) => {
                try {
                    // Handle Enter key for completion
                    if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        onComplete?.();
                    }
                    // Handle Escape key for cancellation
                    if (event.key === "Escape") {
                        event.preventDefault();
                        mathfield.blur();
                    }
                } catch (error) {
                    console.error("Error handling keydown:", error);
                }
            };

            try {
                mathfield.addEventListener("input", handleInput);
                mathfield.addEventListener("focus", handleFocus);
                mathfield.addEventListener("blur", handleBlur);
                mathfield.addEventListener("keydown", handleKeydown);
            } catch (error) {
                console.error("Error adding event listeners:", error);
            }

            return () => {
                try {
                    mathfield.removeEventListener("input", handleInput);
                    mathfield.removeEventListener("focus", handleFocus);
                    mathfield.removeEventListener("blur", handleBlur);
                    mathfield.removeEventListener("keydown", handleKeydown);
                } catch (error) {
                    console.error("Error removing event listeners:", error);
                }
            };
        }, [
            isInitialized,
            value,
            onChange,
            onFocus,
            onBlur,
            onComplete,
            virtualKeyboardMode,
            smartMode,
            readOnly,
            handleMathError,
            deviceInfo,
        ]);

        // Update value when prop changes
        useEffect(() => {
            const mathfield = mathfieldRef.current;
            if (mathfield && mathfield.value !== value) {
                try {
                    mathfield.value = value;
                } catch (error) {
                    console.error("Error updating value:", error);
                }
            }
        }, [value]);

        // Expose methods through ref
        useImperativeHandle(
            ref,
            () => ({
                getValue: () => {
                    try {
                        return mathfieldRef.current?.value || "";
                    } catch (error) {
                        console.error("Error getting value:", error);
                        return "";
                    }
                },
                setValue: (newValue: string) => {
                    try {
                        if (mathfieldRef.current) {
                            mathfieldRef.current.value = newValue;
                        }
                    } catch (error) {
                        console.error("Error setting value:", error);
                    }
                },
                focus: () => {
                    try {
                        mathfieldRef.current?.focus();
                    } catch (error) {
                        console.error("Error focusing:", error);
                    }
                },
                blur: () => {
                    try {
                        mathfieldRef.current?.blur();
                    } catch (error) {
                        console.error("Error blurring:", error);
                    }
                },
                insert: (latex: string) => {
                    try {
                        mathfieldRef.current?.insert(latex);
                    } catch (error) {
                        console.error("Error inserting:", error);
                    }
                },
                clear: () => {
                    try {
                        if (mathfieldRef.current) {
                            mathfieldRef.current.value = "";
                        }
                    } catch (error) {
                        console.error("Error clearing:", error);
                    }
                },
            }),
            []
        );

        // Show fallback UI if MathLive is not initialized
        if (!isInitialized) {
            if (initError) {
                return (
                    <div className={`math-field-error ${className}`} style={style}>
                        <input
                            type="text"
                            value={value}
                            onChange={(e) => onChange?.(e.target.value)}
                            onFocus={onFocus}
                            onBlur={onBlur}
                            placeholder="LaTeX (MathLive unavailable)"
                            className="math-field-fallback"
                        />
                        <div className="math-field-error-message">{initError}</div>
                    </div>
                );
            }

            return (
                <div className={`math-field-loading ${className}`} style={style}>
                    <div className="math-field-spinner">Loading MathLive...</div>
                </div>
            );
        }

        return (
            // @ts-ignore
            <math-field
                ref={mathfieldRef as React.RefObject<HTMLElement>}
                className={className}
                style={style}
                virtual-keyboard-mode={virtualKeyboardMode}
                smart-mode={smartMode}
                read-only={readOnly}
            />
        );
    }
);

MathField.displayName = "MathField";


