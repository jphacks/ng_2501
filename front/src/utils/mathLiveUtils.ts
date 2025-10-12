// MathLive utility functions and initialization

// Import type only for type safety, not for runtime
import type { MathfieldElement } from 'mathlive';
import { validateLatex } from '@/app/datas/MathValidation';

// Check if we're in a browser environment
const isBrowser = typeof window !== 'undefined';

// Re-export validateLatex for backward compatibility
export { validateLatex };

// Check if MathLive is properly loaded
export function isMathLiveLoaded(): boolean {
    try {
        if (!isBrowser) return false;
        return typeof customElements !== 'undefined' &&
            typeof customElements.get('math-field') !== 'undefined';
    } catch (error) {
        console.error('Error checking MathLive availability:', error);
        return false;
    }
}

// Initialize MathLive with error handling
export function initializeMathLive(): Promise<boolean> {
    return new Promise((resolve) => {
        try {
            if (!isBrowser) {
                console.warn('MathLive cannot be initialized in non-browser environment');
                resolve(false);
                return;
            }

            // Check if already loaded
            if (isMathLiveLoaded()) {
                resolve(true);
                return;
            }

            let attempts = 0;
            const maxAttempts = 100; // 10 seconds total (100ms * 100)
            
            // Wait for MathLive to be available
            const checkInterval = setInterval(() => {
                attempts++;
                
                if (isMathLiveLoaded()) {
                    clearInterval(checkInterval);
                    console.log('MathLive loaded successfully');
                    resolve(true);
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    console.error('MathLive failed to load within timeout');
                    resolve(false);
                }
            }, 100);

        } catch (error) {
            console.error('Error initializing MathLive:', error);
            resolve(false);
        }
    });
}

// Safe MathField creation with error handling
export function createSafeMathField(): MathfieldElement | null {
    try {
        if (!isBrowser || !isMathLiveLoaded()) {
            console.error('MathLive is not loaded or not in browser environment');
            return null;
        }

        const mathfield = document.createElement('math-field') as MathfieldElement;
        return mathfield;
    } catch (error) {
        console.error('Error creating MathField:', error);
        return null;
    }
}


// Safe LaTeX rendering test
export function testLatexRendering(latex: string): Promise<boolean> {
    return new Promise((resolve) => {
        try {
            if (!isMathLiveLoaded()) {
                resolve(false);
                return;
            }

            const testField = createSafeMathField();
            if (!testField) {
                resolve(false);
                return;
            }

            // Test rendering in a temporary element
            const tempContainer = document.createElement('div');
            tempContainer.style.position = 'absolute';
            tempContainer.style.left = '-9999px';
            tempContainer.style.top = '-9999px';
            tempContainer.appendChild(testField);
            document.body.appendChild(tempContainer);

            try {
                testField.value = latex;
                // If we get here without error, rendering succeeded
                document.body.removeChild(tempContainer);
                resolve(true);
            } catch (error) {
                console.error('LaTeX rendering test failed:', error);
                document.body.removeChild(tempContainer);
                resolve(false);
            }
        } catch (error) {
            console.error('Error testing LaTeX rendering:', error);
            resolve(false);
        }
    });
}

// Get MathLive version info
export function getMathLiveInfo(): { version?: string; loaded: boolean } {
    try {
        const loaded = isMathLiveLoaded();
        return {
            loaded,
            version: loaded ? 'unknown' : undefined // MathLive doesn't expose version easily
        };
    } catch (error) {
        return { loaded: false };
    }
}


