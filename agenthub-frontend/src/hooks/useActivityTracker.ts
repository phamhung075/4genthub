import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from './useAuth';
import logger from '../utils/logger';

interface ActivityTrackerOptions {
  idleTimeoutMinutes?: number;
  refreshBeforeExpiryMinutes?: number;
  activities?: string[];
}

/**
 * Hook to track user activity and refresh tokens proactively
 * This prevents session timeouts during active usage
 */
export const useActivityTracker = (options: ActivityTrackerOptions = {}) => {
  const {
    idleTimeoutMinutes = 30,
    refreshBeforeExpiryMinutes = 5,
    activities = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click']
  } = options;

  const { tokens, refreshToken, isAuthenticated } = useAuth();
  const lastActivityRef = useRef<Date>(new Date());
  const refreshTimerRef = useRef<NodeJS.Timeout>();

  const scheduleTokenRefresh = useCallback(() => {
    if (!tokens?.access_token || !isAuthenticated) return;

    // Clear existing timer
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }

    try {
      const payload = JSON.parse(atob(tokens.access_token.split('.')[1]));
      const expiryTime = payload.exp * 1000;
      const currentTime = Date.now();
      const refreshTime = expiryTime - (refreshBeforeExpiryMinutes * 60 * 1000);
      const timeUntilRefresh = Math.max(0, refreshTime - currentTime);

      refreshTimerRef.current = setTimeout(async () => {
        try {
          logger.info('🔄 Activity-based token refresh triggered');
          await refreshToken();
        } catch (error) {
          logger.error('❌ Activity-based token refresh failed:', error);
        }
      }, timeUntilRefresh);

      logger.debug(`⏰ Token refresh scheduled in ${Math.round(timeUntilRefresh / 1000 / 60)} minutes`);
    } catch (error) {
      logger.error('❌ Failed to schedule token refresh:', error);
    }
  }, [tokens, refreshToken, isAuthenticated, refreshBeforeExpiryMinutes]);

  const handleActivity = useCallback(() => {
    lastActivityRef.current = new Date();
    scheduleTokenRefresh();
  }, [scheduleTokenRefresh]);

  useEffect(() => {
    if (!isAuthenticated) return;

    // Add activity listeners
    activities.forEach(activity => {
      window.addEventListener(activity, handleActivity, { passive: true });
    });

    // Initial setup
    handleActivity();

    // Cleanup
    return () => {
      activities.forEach(activity => {
        window.removeEventListener(activity, handleActivity);
      });
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [isAuthenticated, activities, handleActivity]);

  return {
    lastActivity: lastActivityRef.current,
    isIdle: Date.now() - lastActivityRef.current.getTime() > (idleTimeoutMinutes * 60 * 1000)
  };
};