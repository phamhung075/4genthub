/**
 * WebSocket Toast Bridge Component
 *
 * This component bridges the WebSocket service's toast event bus
 * with the app's toast context, allowing WebSocket events to trigger
 * toast notifications using the existing toast UI system.
 */

import { useEffect } from 'react';
import { toastEventBus, ToastEvent } from '../services/toastEventBus';
import { useSuccessToast, useErrorToast, useWarningToast, useInfoToast } from './ui/toast';

export const WebSocketToastBridge: React.FC = () => {
  const showSuccessToast = useSuccessToast();
  const showErrorToast = useErrorToast();
  const showWarningToast = useWarningToast();
  const showInfoToast = useInfoToast();

  useEffect(() => {
    // Subscribe to toast events from the WebSocket service
    const unsubscribe = toastEventBus.subscribe((event: ToastEvent) => {
      switch (event.type) {
        case 'success':
          showSuccessToast(event.title, event.description, event.action);
          break;
        case 'error':
          showErrorToast(event.title, event.description, event.action);
          break;
        case 'warning':
          showWarningToast(event.title, event.description, event.action);
          break;
        case 'info':
          showInfoToast(event.title, event.description, event.action);
          break;
      }
    });

    // Request notification permission on mount if not already granted
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Cleanup on unmount
    return unsubscribe;
  }, [showSuccessToast, showErrorToast, showWarningToast, showInfoToast]);

  // This component doesn't render anything visible
  return null;
};