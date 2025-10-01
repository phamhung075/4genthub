import { useEffect, useCallback, useRef, useMemo } from 'react';
import {
  changePoolService,
  ComponentSubscription,
  EntityType,
  ChangeNotification
} from '../services/changePoolService';

interface UseChangeSubscriptionOptions {
  componentId: string;
  entityTypes: EntityType[];
  entityIds?: string[];
  projectId?: string;
  branchId?: string;
  refreshCallback: (notification?: ChangeNotification) => void; // FIXED: Accept notification data
  shouldRefresh?: (notification: ChangeNotification) => boolean;
  enabled?: boolean; // Allow disabling subscription conditionally
}

/**
 * React hook for subscribing to entity changes through the centralized change pool
 *
 * Usage:
 * ```tsx
 * const ProjectList = () => {
 *   const [projects, setProjects] = useState([]);
 *
 *   const fetchProjects = useCallback(() => {
 *     // Your API call to fetch projects
 *   }, []);
 *
 *   useChangeSubscription({
 *     componentId: 'ProjectList',
 *     entityTypes: ['project', 'branch'],
 *     refreshCallback: fetchProjects
 *   });
 *
 *   return <div>Your component content</div>;
 * };
 * ```
 */
export function useChangeSubscription(options: UseChangeSubscriptionOptions) {
  const {
    componentId,
    entityTypes,
    entityIds,
    projectId,
    branchId,
    refreshCallback,
    shouldRefresh,
    enabled = true
  } = options;

  const unsubscribeRef = useRef<(() => void) | null>(null);

  // Stable reference to refresh callback - FIXED: Pass notification data through
  const stableRefreshCallback = useCallback((notification?: ChangeNotification) => {
    logger.debug(`🔧 [useChangeSubscription] ${componentId}: Passing notification to refreshCallback`, {
      hasNotification: !!notification,
      entityType: notification?.entityType,
      eventType: notification?.eventType,
      entityId: notification?.entityId
    });
    refreshCallback(notification);
  }, [refreshCallback, componentId]);

  // Stable array references to prevent unnecessary re-subscriptions
  const stableEntityTypes = useMemo(() => entityTypes, [JSON.stringify(entityTypes)]);
  const stableEntityIds = useMemo(() => entityIds, [JSON.stringify(entityIds)]);

  useEffect(() => {
    // Only subscribe if enabled
    if (!enabled) {
      return;
    }

    // Clean up existing subscription
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    // Create new subscription
    const subscription: ComponentSubscription = {
      componentId,
      entityTypes: stableEntityTypes,
      entityIds: stableEntityIds,
      projectId,
      branchId,
      refreshCallback: stableRefreshCallback,
      shouldRefresh
    };

    const unsubscribe = changePoolService.subscribe(subscription);
    unsubscribeRef.current = unsubscribe;

    // Cleanup on unmount or dependency change
    return () => {
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    };
  }, [
    componentId,
    stableEntityTypes,
    stableEntityIds,
    projectId,
    branchId,
    stableRefreshCallback,
    shouldRefresh,
    enabled
  ]);
}

/**
 * Simplified hook for common use cases
 */
export function useEntityChanges(
  componentId: string,
  entityTypes: EntityType | EntityType[],
  refreshCallback: (notification?: ChangeNotification) => void, // FIXED: Accept notification data
  options?: {
    projectId?: string;
    branchId?: string;
    entityIds?: string[];
    enabled?: boolean;
  }
) {
  const entityTypesArray = Array.isArray(entityTypes) ? entityTypes : [entityTypes];

  useChangeSubscription({
    componentId,
    entityTypes: entityTypesArray,
    refreshCallback,
    ...options
  });
}