// Error handling utilities and custom error classes

// Math rendering error class
export class MathRenderError extends Error {
    public latex: string;
    public cause?: Error;

    constructor(message: string, latex: string, cause?: Error) {
        super(message);
        this.name = 'MathRenderError';
        this.latex = latex;
        this.cause = cause;
    }
}

// Generic application error class
export class AppError extends Error {
    public code: string;
    public severity: 'low' | 'medium' | 'high';
    public cause?: Error;

    constructor(
        message: string,
        code: string,
        severity: 'low' | 'medium' | 'high' = 'medium',
        cause?: Error
    ) {
        super(message);
        this.name = 'AppError';
        this.code = code;
        this.severity = severity;
        this.cause = cause;
    }
}

// Error message mapping for user-friendly messages
export const ERROR_MESSAGES = {
    // Math rendering errors
    MATH_RENDER_FAILED: 'Failed to render math expression. Please check the LaTeX syntax.',
    MATH_INVALID_SYNTAX: 'Invalid LaTeX syntax in math expression.',
    MATH_EDITOR_FAILED: 'Math editor failed to initialize. Please refresh the page.',

    // General errors
    NETWORK_ERROR: 'Network connection error. Please check your internet connection.',
    UNKNOWN_ERROR: 'An unexpected error occurred. Please try again.',
    COMPONENT_ERROR: 'A component error occurred. The page will be refreshed.',
};

// Error severity levels
export const ErrorSeverity = {
    LOW: 'low',
    MEDIUM: 'medium',
    HIGH: 'high'
} as const;
export type ErrorSeverity = typeof ErrorSeverity[keyof typeof ErrorSeverity];

// Error categories
export const ErrorCategory = {
    MATH: 'math',
    NETWORK: 'network',
    COMPONENT: 'component',
    UNKNOWN: 'unknown'
} as const;
export type ErrorCategory = typeof ErrorCategory[keyof typeof ErrorCategory];

// Error classification utility
export function classifyError(error: Error): { category: ErrorCategory; severity: ErrorSeverity; userMessage: string } {
    // Math rendering errors
    if (error.name === 'MathRenderError') {
        return {
            category: ErrorCategory.MATH,
            severity: ErrorSeverity.LOW,
            userMessage: ERROR_MESSAGES.MATH_RENDER_FAILED
        };
    }

    // Network errors
    if (error.message.includes('network') || error.message.includes('fetch')) {
        return {
            category: ErrorCategory.NETWORK,
            severity: ErrorSeverity.MEDIUM,
            userMessage: ERROR_MESSAGES.NETWORK_ERROR
        };
    }

    // Component errors (React errors)
    if (error.message.includes('React') || error.stack?.includes('React')) {
        return {
            category: ErrorCategory.COMPONENT,
            severity: ErrorSeverity.HIGH,
            userMessage: ERROR_MESSAGES.COMPONENT_ERROR
        };
    }

    // Default unknown error
    return {
        category: ErrorCategory.UNKNOWN,
        severity: ErrorSeverity.MEDIUM,
        userMessage: ERROR_MESSAGES.UNKNOWN_ERROR
    };
}

// Error logging utility
export function logError(error: Error, context?: string): void {
    const { category, severity } = classifyError(error);

    const errorInfo = {
        message: error.message,
        name: error.name,
        stack: error.stack,
        category,
        severity,
        context,
        timestamp: new Date().toISOString(),
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
        url: typeof window !== 'undefined' ? window.location.href : 'unknown'
    };

    // Log to console with appropriate level
    if (severity === ErrorSeverity.HIGH) {
        console.error('High severity error:', errorInfo);
    } else if (severity === ErrorSeverity.MEDIUM) {
        console.warn('Medium severity error:', errorInfo);
    } else {
        console.info('Low severity error:', errorInfo);
    }
}

// Safe async operation wrapper
export async function safeAsync<T>(
    operation: () => Promise<T>,
    fallback?: T,
    onError?: (error: Error) => void
): Promise<T | undefined> {
    try {
        return await operation();
    } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        logError(err, 'safeAsync operation');

        if (onError) {
            onError(err);
        }

        return fallback;
    }
}


