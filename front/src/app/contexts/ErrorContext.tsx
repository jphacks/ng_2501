'use client'

import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { logError } from '@/app/datas/MathError';
import type { ErrorNotification } from '@/app/datas/MathExpression';

interface ErrorContextValue {
    notifications: ErrorNotification[];
    showNotification: (notification: Omit<ErrorNotification, 'id' | 'timestamp'>) => void;
    showError: (error: Error, context?: string) => void;
    dismissNotification: (id: string) => void;
    clearNotifications: () => void;
}

const ErrorContext = createContext<ErrorContextValue | undefined>(undefined);

interface ErrorProviderProps {
    children: ReactNode;
}

export const ErrorProvider: React.FC<ErrorProviderProps> = ({ children }) => {
    const [notifications, setNotifications] = useState<ErrorNotification[]>([]);

    const showNotification = useCallback((notification: Omit<ErrorNotification, 'id' | 'timestamp'>) => {
        const newNotification: ErrorNotification = {
            ...notification,
            id: `${Date.now()}-${Math.random()}`,
            timestamp: new Date(),
        };

        setNotifications(prev => [...prev, newNotification]);

        // Auto-hide if specified
        if (notification.autoHide) {
            const duration = notification.duration || 5000;
            setTimeout(() => {
                setNotifications(prev => prev.filter(n => n.id !== newNotification.id));
            }, duration);
        }
    }, []);

    const showError = useCallback((error: Error, context?: string) => {
        logError(error, context);

        showNotification({
            type: 'error',
            title: 'エラー',
            message: error.message || 'エラーが発生しました',
            dismissible: true,
            autoHide: true,
            duration: 5000,
        });
    }, [showNotification]);

    const dismissNotification = useCallback((id: string) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    const clearNotifications = useCallback(() => {
        setNotifications([]);
    }, []);

    const contextValue: ErrorContextValue = {
        notifications,
        showNotification,
        showError,
        dismissNotification,
        clearNotifications,
    };

    return (
        <ErrorContext.Provider value={contextValue}>
            {children}
        </ErrorContext.Provider>
    );
};

export const useError = (): ErrorContextValue => {
    const context = useContext(ErrorContext);
    if (context === undefined) {
        throw new Error('useError must be used within an ErrorProvider');
    }
    return context;
};

// Convenience hooks for common error scenarios
export const useMathError = () => {
    const { showError } = useError();

    return {
        handleMathError: (error: Error, latex?: string) => {
            showError(error, latex ? `Math rendering: ${latex}` : 'Math rendering');
        }
    };
};


