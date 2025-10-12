import { useRef, useCallback, useState } from 'react';
import type { MathFieldRef } from '@/components/math/MathField';

// Configuration options for MathField
export interface MathFieldConfig {
    virtualKeyboardMode?: 'manual' | 'onfocus' | 'off';
    smartMode?: boolean;
    readOnly?: boolean;
    initialValue?: string;
}

// Return type for useMathField hook
export interface UseMathFieldReturn {
    mathFieldRef: React.RefObject<MathFieldRef | null>;
    value: string;
    setValue: (value: string) => void;
    getValue: () => string;
    focus: () => void;
    blur: () => void;
    insert: (latex: string) => void;
    clear: () => void;
    isActive: boolean;
    setIsActive: (active: boolean) => void;
}

/**
 * Custom hook for managing MathField component state and interactions
 * Provides a convenient interface for working with MathLive in React
 */
export const useMathField = (config: MathFieldConfig = {}): UseMathFieldReturn => {
    const mathFieldRef = useRef<MathFieldRef>(null);
    const [value, setValue] = useState(config.initialValue || '');
    const [isActive, setIsActive] = useState(false);

    // Get current value from the MathField
    const getValue = useCallback((): string => {
        try {
            return mathFieldRef.current?.getValue() || value;
        } catch (error) {
            console.error('Error getting MathField value:', error);
            return value;
        }
    }, [value]);

    // Set value in the MathField
    const setValueCallback = useCallback((newValue: string) => {
        try {
            setValue(newValue);
            mathFieldRef.current?.setValue(newValue);
        } catch (error) {
            console.error('Error setting MathField value:', error);
            setValue(newValue); // At least update the state
        }
    }, []);

    // Focus the MathField
    const focus = useCallback(() => {
        try {
            const mathField = mathFieldRef.current;
            if (mathField) {
                mathField.focus();
                // Add a small delay to ensure focus is applied
                setTimeout(() => {
                    // Try focusing again as a fallback
                    mathField.focus();
                }, 50);
            }
            setIsActive(true);
        } catch (error) {
            console.error('Error focusing MathField:', error);
            setIsActive(true); // Update state even if focus fails
        }
    }, []);

    // Blur the MathField
    const blur = useCallback(() => {
        try {
            mathFieldRef.current?.blur();
            setIsActive(false);
        } catch (error) {
            console.error('Error blurring MathField:', error);
            setIsActive(false); // Update state even if blur fails
        }
    }, []);

    // Insert LaTeX at current cursor position
    const insert = useCallback((latex: string) => {
        try {
            mathFieldRef.current?.insert(latex);
        } catch (error) {
            console.error('Error inserting into MathField:', error);
        }
    }, []);

    // Clear the MathField
    const clear = useCallback(() => {
        try {
            setValue('');
            mathFieldRef.current?.clear();
        } catch (error) {
            console.error('Error clearing MathField:', error);
            setValue(''); // At least clear the state
        }
    }, []);

    return {
        mathFieldRef,
        value,
        setValue: setValueCallback,
        getValue,
        focus,
        blur,
        insert,
        clear,
        isActive,
        setIsActive,
    };
};


