// Domain層: Math式のバリデーションロジック

/**
 * LaTeX式のバリデーション
 */
export function validateLatex(latex: string): { isValid: boolean; error?: string } {
    try {
        if (!latex || typeof latex !== 'string') {
            return { isValid: false, error: 'Invalid LaTeX input' };
        }

        // Basic LaTeX validation
        const openBraces = (latex.match(/\{/g) || []).length;
        const closeBraces = (latex.match(/\}/g) || []).length;

        if (openBraces !== closeBraces) {
            return { isValid: false, error: 'Mismatched braces in LaTeX' };
        }

        // Check for common LaTeX errors
        const invalidPatterns = [
            /\\[a-zA-Z]+\s*\{[^}]*$/,  // Unclosed command
            /\$\$[^$]*\$(?!\$)/,       // Mismatched display math delimiters
            /\$[^$]*\$\$/,             // Mismatched inline math delimiters
        ];

        for (const pattern of invalidPatterns) {
            if (pattern.test(latex)) {
                return { isValid: false, error: 'Invalid LaTeX syntax' };
            }
        }

        return { isValid: true };
    } catch (error) {
        return { isValid: false, error: 'Error validating LaTeX' };
    }
}

