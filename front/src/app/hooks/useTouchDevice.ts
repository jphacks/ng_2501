import { useState, useEffect } from 'react';
import {
    isTouchDevice,
    isMobileDevice,
    isTabletDevice,
    getViewportInfo,
    debounce
} from '@/utils/touchUtils';

export interface TouchDeviceInfo {
    isTouch: boolean;
    isMobile: boolean;
    isTablet: boolean;
    isDesktop: boolean;
    orientation: 'portrait' | 'landscape';
    viewportWidth: number;
    viewportHeight: number;
    pixelRatio: number;
    hasPhysicalKeyboard: boolean;
}

export interface UseTouchDeviceReturn {
    deviceInfo: TouchDeviceInfo;
    isLoading: boolean;
}

export const useTouchDevice = (): UseTouchDeviceReturn => {
    const [deviceInfo, setDeviceInfo] = useState<TouchDeviceInfo>(() => {
        // Initialize with safe defaults
        return {
            isTouch: false,
            isMobile: false,
            isTablet: false,
            isDesktop: true,
            orientation: 'landscape',
            viewportWidth: 1024,
            viewportHeight: 768,
            pixelRatio: 1,
            hasPhysicalKeyboard: true
        };
    });

    const [isLoading, setIsLoading] = useState(true);

    // Update device info
    const updateDeviceInfo = () => {
        try {
            const viewport = getViewportInfo();
            const isTouch = isTouchDevice();
            const isMobile = isMobileDevice();
            const isTablet = isTabletDevice();
            const isDesktop = !isMobile && !isTablet;

            setDeviceInfo({
                isTouch,
                isMobile,
                isTablet,
                isDesktop,
                orientation: viewport.orientation,
                viewportWidth: viewport.width,
                viewportHeight: viewport.height,
                pixelRatio: viewport.pixelRatio,
                hasPhysicalKeyboard: viewport.hasPhysicalKeyboard
            });
        } catch (error) {
            console.error('Error updating device info:', error);
        }
    };

    // Initialize device info
    useEffect(() => {
        updateDeviceInfo();
        setIsLoading(false);
    }, []);

    // Listen for viewport changes
    useEffect(() => {
        const debouncedUpdate = debounce(updateDeviceInfo, 250);

        window.addEventListener('resize', debouncedUpdate);
        window.addEventListener('orientationchange', debouncedUpdate);

        return () => {
            window.removeEventListener('resize', debouncedUpdate);
            window.removeEventListener('orientationchange', debouncedUpdate);
        };
    }, []);

    return {
        deviceInfo,
        isLoading
    };
};


