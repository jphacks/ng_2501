// Math utilities for detecting and manipulating math expressions in markdown

// Math expression in markdown content
export interface MathExpression {
    latex: string;
    start: number;
    end: number;
    isInline: boolean;
    raw: string;
}

// Math editor state
export interface MathContext {
    activeNode?: string;
    editMode: boolean;
}

// Editor state management
export interface EditorState {
    content: string;
    cursorPosition: number;
    selectedText: string;
    isEditing: boolean;
    mathEditMode: boolean;
}

// Error handling types
export interface ErrorInfo {
    componentStack: string | undefined;
    errorBoundary?: string;
}

export interface ErrorNotification {
    id: string;
    type: 'error' | 'warning' | 'info' | 'success';
    title: string;
    message: string;
    timestamp: Date;
    dismissible: boolean;
    autoHide?: boolean;
    duration?: number;
}

/**
 * Extract all math expressions from markdown content
 */
export function extractMathExpressions(content: string): MathExpression[] {
    const expressions: MathExpression[] = [];

    // Regex patterns for math expressions
    const blockMathRegex = /\$\$([^$]*?)\$\$/g;
    const inlineMathRegex = /\$([^$\n]*?)\$/g;

    // Find block math expressions first (they take precedence)
    let match;
    while ((match = blockMathRegex.exec(content)) !== null) {
        expressions.push({
            latex: match[1].trim(),
            start: match.index,
            end: match.index + match[0].length,
            isInline: false,
            raw: match[0]
        });
    }

    // Find inline math expressions, excluding those already found in blocks
    const blockRanges = expressions.map(expr => ({ start: expr.start, end: expr.end }));

    // Reset regex
    inlineMathRegex.lastIndex = 0;

    while ((match = inlineMathRegex.exec(content)) !== null) {
        const start = match.index;
        const end = match.index + match[0].length;

        // Check if this inline math is inside a block math expression
        const isInsideBlock = blockRanges.some(range =>
            start >= range.start && end <= range.end
        );

        if (!isInsideBlock) {
            expressions.push({
                latex: match[1].trim(),
                start,
                end,
                isInline: true,
                raw: match[0]
            });
        }
    }

    // Sort by position
    return expressions.sort((a, b) => a.start - b.start);
}

/**
 * Check if a cursor position is inside a math expression
 */
export function getMathExpressionAtPosition(content: string, position: number): MathExpression | null {
    const expressions = extractMathExpressions(content);
    return expressions.find(expr => position >= expr.start && position <= expr.end) || null;
}

/**
 * Replace a math expression in content with new LaTeX
 */
export function replaceMathExpression(
    content: string,
    expression: MathExpression,
    newLatex: string
): string {
    const delimiter = expression.isInline ? '$' : '$$';
    const newMathText = expression.isInline
        ? `${delimiter}${newLatex}${delimiter}`
        : `${delimiter}\n${newLatex}\n${delimiter}`;

    return content.substring(0, expression.start) +
        newMathText +
        content.substring(expression.end);
}

/**
 * Insert math expression at a specific position
 */
export function insertMathExpression(
    content: string,
    position: number,
    latex: string,
    isInline: boolean = true
): { content: string; newCursorPosition: number } {
    const delimiter = isInline ? '$' : '$$';
    const mathText = isInline
        ? `${delimiter}${latex}${delimiter}`
        : `\n${delimiter}\n${latex}\n${delimiter}\n`;

    const newContent = content.substring(0, position) +
        mathText +
        content.substring(position);

    const newCursorPosition = position + mathText.length;

    return { content: newContent, newCursorPosition };
}

/**
 * Get common math shortcuts and their LaTeX equivalents
 */
export function getMathShortcuts(): Record<string, string> {
    return {
        // Greek letters
        'alpha': '\\alpha',
        'beta': '\\beta',
        'gamma': '\\gamma',
        'delta': '\\delta',
        'epsilon': '\\epsilon',
        'zeta': '\\zeta',
        'eta': '\\eta',
        'theta': '\\theta',
        'iota': '\\iota',
        'kappa': '\\kappa',
        'lambda': '\\lambda',
        'mu': '\\mu',
        'nu': '\\nu',
        'xi': '\\xi',
        'pi': '\\pi',
        'rho': '\\rho',
        'sigma': '\\sigma',
        'tau': '\\tau',
        'phi': '\\phi',
        'chi': '\\chi',
        'psi': '\\psi',
        'omega': '\\omega',

        // Math operators
        'sum': '\\sum',
        'prod': '\\prod',
        'int': '\\int',
        'oint': '\\oint',
        'lim': '\\lim',
        'inf': '\\infty',
        'infty': '\\infty',
        'partial': '\\partial',
        'nabla': '\\nabla',

        // Functions
        'frac': '\\frac{#@}{#?}',
        'sqrt': '\\sqrt{#@}',
        'cbrt': '\\sqrt[3]{#@}',
        'sin': '\\sin',
        'cos': '\\cos',
        'tan': '\\tan',
        'log': '\\log',
        'ln': '\\ln',
        'exp': '\\exp',

        // Arrows
        'to': '\\to',
        'rightarrow': '\\rightarrow',
        'leftarrow': '\\leftarrow',
        'leftrightarrow': '\\leftrightarrow',
        'Rightarrow': '\\Rightarrow',
        'Leftarrow': '\\Leftarrow',
        'Leftrightarrow': '\\Leftrightarrow',

        // Relations
        'leq': '\\leq',
        'geq': '\\geq',
        'neq': '\\neq',
        'approx': '\\approx',
        'equiv': '\\equiv',
        'propto': '\\propto',
        'in': '\\in',
        'notin': '\\notin',
        'subset': '\\subset',
        'supset': '\\supset',
        'subseteq': '\\subseteq',
        'supseteq': '\\supseteq',

        // Sets
        'emptyset': '\\emptyset',
        'cup': '\\cup',
        'cap': '\\cap',
        'union': '\\cup',
        'intersection': '\\cap',

        // Logic
        'land': '\\land',
        'lor': '\\lor',
        'lnot': '\\lnot',
        'forall': '\\forall',
        'exists': '\\exists',

        // Miscellaneous
        'pm': '\\pm',
        'mp': '\\mp',
        'cdot': '\\cdot',
        'times': '\\times',
        'div': '\\div',
        'ast': '\\ast',
        'star': '\\star',
        'circ': '\\circ',
        'bullet': '\\bullet',
        'oplus': '\\oplus',
        'ominus': '\\ominus',
        'otimes': '\\otimes',
        'oslash': '\\oslash',
    };
}


