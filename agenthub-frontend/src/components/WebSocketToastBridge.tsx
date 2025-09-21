/**
 * WebSocket Toast Bridge Component
 *
 * This component bridges the WebSocket service's toast event bus
 * with the app's toast context, allowing WebSocket events to trigger
 * toast notifications using the existing toast UI system.
 */

import { useEffect } from 'react';
import { toastEventBus, ToastEvent } from '../services/toastEventBus';
import { useToast } from './ui/toast';

export const WebSocketToastBridge: React.FC = () => {
  const { showToast } = useToast();

  useEffect(() => {
    console.log('🔌 WebSocketToastBridge: Component mounted, subscribing to toastEventBus');

    // Subscribe to toast events from the WebSocket service
    const unsubscribe = toastEventBus.subscribe((event: ToastEvent) => {
      console.log('🔔 WebSocketToastBridge: Received toast event from toastEventBus:', event);

      // Use the stable showToast function directly instead of individual hook functions
      const toastId = showToast({
        type: event.type,
        title: event.title,
        description: event.description,
        action: event.action,
        // Set appropriate durations for different types
        duration: event.type === 'error' ? 8000 : 5000
      });

      console.log('✅ WebSocketToastBridge: Called showToast, returned ID:', toastId);
    });

    // Request notification permission on mount if not already granted
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    // Cleanup on unmount
    return unsubscribe;
  }, []); // Empty dependency array since showToast should be stable

  // This component doesn't render anything visible
  return null;
};