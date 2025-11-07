/**
 * Agent Management Custom Hooks (React Query version)
 *
 * Provides React hooks for interacting with the User-Specific Agent System.
 * Uses React Query for automatic caching, mutations, and optimistic updates.
 *
 * @module hooks/useAgentManagement
 * @version 2.0.0
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentManagementApiV2 } from '../services/apiV2';
import logger from '../utils/logger';
import { useSuccessToast, useWarningToast } from '../components/ui/toast';
import type {
  AgentTemplate,
  UserAgentInstance,
  CreateInstanceRequest,
  UpdateInstanceRequest,
  ShareAgentResponse,
  MarketplaceAgent,
  SharedAgentPreviewResponse,
  UserUsageStats,
  PopularAgentStats,
  MarketplaceFilters,
} from '../types/agentTypes';

// ============================================================================
// useAgentTemplates - List and manage agent templates
// ============================================================================

interface UseAgentTemplatesReturn {
  templates: AgentTemplate[];
  loading: boolean;
  error: string | null;
  loadTemplates: () => Promise<void>;
  getTemplateBySlug: (slug: string) => AgentTemplate | undefined;
}

/**
 * Hook for managing agent templates from agent-library
 * Templates are read-only system-wide templates that users can instantiate
 */
export function useAgentTemplates(): UseAgentTemplatesReturn {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['agentTemplates'],
    queryFn: async () => {
      const response: any = await agentManagementApiV2.listTemplates();
      if (response.success && response.templates) {
        logger.info(`Loaded ${response.templates.length} agent templates`);
        return response.templates;
      }
      throw new Error(response.message || 'Failed to load templates');
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - templates rarely change
  });

  const getTemplateBySlug = useCallback((slug: string) => {
    return data?.find((t: AgentTemplate) => t.slug === slug);
  }, [data]);

  return {
    templates: data ?? [],
    loading: isLoading,
    error: error?.message ?? null,
    loadTemplates: refetch,
    getTemplateBySlug,
  };
}

// ============================================================================
// useUserAgentInstances - Manage user's agent instances (React Query + Mutations)
// ============================================================================

interface UseUserAgentInstancesReturn {
  instances: UserAgentInstance[];
  isLoading: boolean;
  error: string | null;
  loadInstances: () => Promise<void>;
  getInstance: (instanceId: string) => Promise<UserAgentInstance | null>;
  createInstance: (data: CreateInstanceRequest) => Promise<UserAgentInstance | null>;
  updateInstance: (instanceId: string, data: UpdateInstanceRequest) => Promise<UserAgentInstance | null>;
  deleteInstance: (instanceId: string) => Promise<boolean>;
  refreshInstance: (instanceId: string) => Promise<void>;
  toggleEnabled: (instanceId: string, enabled: boolean) => Promise<boolean>;
}

/**
 * Hook for managing user's agent instances with React Query mutations
 * Handles CRUD operations with automatic cache updates
 */
export function useUserAgentInstances(): UseUserAgentInstancesReturn {
  const queryClient = useQueryClient();
  const showSuccess = useSuccessToast();
  const showWarning = useWarningToast();

  // Query for listing instances
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['userAgentInstances'],
    queryFn: async () => {
      const response: any = await agentManagementApiV2.listUserInstances();
      if (response.success && response.instances) {
        logger.info(`Loaded ${response.instances.length} agent instances`);
        return response.instances;
      }
      throw new Error(response.message || 'Failed to load instances');
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Mutation for creating instance
  const createMutation = useMutation({
    mutationFn: (data: CreateInstanceRequest) => agentManagementApiV2.createInstance(data),
    onSuccess: (newInstance) => {
      // Optimistic update
      queryClient.setQueryData(['userAgentInstances'], (old: UserAgentInstance[] = []) =>
        [...old, newInstance]
      );
      // CRITICAL FIX: Invalidate to trigger re-render
      queryClient.invalidateQueries({ queryKey: ['userAgentInstances'] });
      // CRITICAL FIX: Direct notification (backup to WebSocket)
      showSuccess(`Agent "${newInstance.agent_name}" created successfully`);
      logger.info(`Created instance: ${newInstance.agent_name}`);
    },
  });

  // Mutation for updating instance
  const updateMutation = useMutation({
    mutationFn: ({ instanceId, data }: { instanceId: string; data: UpdateInstanceRequest }) =>
      agentManagementApiV2.updateInstance(instanceId, data),
    onSuccess: (updatedInstance, { instanceId }) => {
      // Optimistic update
      queryClient.setQueryData(['userAgentInstances'], (old: UserAgentInstance[] = []) =>
        old.map(inst => inst.id === instanceId ? updatedInstance : inst)
      );
      // CRITICAL FIX: Invalidate to trigger re-render
      queryClient.invalidateQueries({ queryKey: ['userAgentInstances'] });
      // CRITICAL FIX: Direct notification (backup to WebSocket)
      showSuccess(`Agent "${updatedInstance.agent_name}" updated successfully`);
      logger.info(`Updated instance: ${instanceId}`);
    },
  });

  // Mutation for deleting instance
  const deleteMutation = useMutation({
    mutationFn: (instanceId: string) => agentManagementApiV2.deleteInstance(instanceId),
    onSuccess: (response, instanceId) => {
      // Optimistic update
      queryClient.setQueryData(['userAgentInstances'], (old: UserAgentInstance[] = []) =>
        old.filter(inst => inst.id !== instanceId)
      );
      // CRITICAL FIX: Invalidate to trigger re-render
      queryClient.invalidateQueries({ queryKey: ['userAgentInstances'] });
      // CRITICAL FIX: Direct notification (backup to WebSocket)
      showWarning('Agent deleted successfully');
      logger.info(`Deleted instance: ${instanceId}`);
    },
  });

  // Helper functions
  const getInstance = useCallback(async (instanceId: string): Promise<UserAgentInstance | null> => {
    try {
      const response: any = await agentManagementApiV2.getUserInstance(instanceId);
      if (response.success && response.instance) {
        return response.instance;
      }
      throw new Error(response.message || 'Failed to get instance');
    } catch (err) {
      logger.error(`Error getting instance ${instanceId}:`, err);
      return null;
    }
  }, []);

  const refreshInstance = useCallback(async (instanceId: string) => {
    const instance = await getInstance(instanceId);
    if (instance) {
      queryClient.setQueryData(['userAgentInstances'], (old: UserAgentInstance[] = []) =>
        old.map(inst => inst.id === instanceId ? instance : inst)
      );
    }
  }, [getInstance, queryClient]);

  const toggleEnabled = useCallback(async (instanceId: string, enabled: boolean): Promise<boolean> => {
    try {
      const result = await updateMutation.mutateAsync({ instanceId, data: { is_enabled: enabled } });
      logger.info(`${enabled ? 'Enabled' : 'Disabled'} agent: ${instanceId}`);
      return true;
    } catch (err) {
      logger.error('Error toggling enabled status:', err);
      return false;
    }
  }, [updateMutation]);

  return {
    instances: data ?? [],
    isLoading: isLoading || createMutation.isPending || updateMutation.isPending || deleteMutation.isPending,
    error: error?.message ?? null,
    loadInstances: refetch,
    getInstance,
    createInstance: (data) => createMutation.mutateAsync(data),
    updateInstance: (instanceId, data) => updateMutation.mutateAsync({ instanceId, data }),
    deleteInstance: async (instanceId) => {
      try {
        await deleteMutation.mutateAsync(instanceId);
        return true;
      } catch {
        return false;
      }
    },
    refreshInstance,
    toggleEnabled,
  };
}

// ============================================================================
// useAgentSharing - Manage agent sharing (share/unshare/import)
// ============================================================================

interface UseAgentSharingReturn {
  loading: boolean;
  error: string | null;
  shareAgent: (instanceId: string) => Promise<ShareAgentResponse | null>;
  unshareAgent: (instanceId: string) => Promise<boolean>;
  importAgent: (shareToken: string) => Promise<UserAgentInstance | null>;
}

/**
 * Hook for agent sharing operations
 * Handles sharing agents publicly, unsharing, and importing shared agents
 */
export function useAgentSharing(): UseAgentSharingReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const shareAgent = useCallback(async (instanceId: string): Promise<ShareAgentResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.shareAgent(instanceId);

      if (response.success) {
        logger.info(`Shared agent: ${instanceId}`, {
          shareToken: response.share_token,
          url: response.shareable_url,
        });
        return response as ShareAgentResponse;
      }

      throw new Error(response.message || 'Failed to share agent');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error sharing agent';
      logger.error('Error sharing agent:', err);
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const unshareAgent = useCallback(async (instanceId: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.unshareAgent(instanceId);

      if (response.success) {
        logger.info(`Unshared agent: ${instanceId}`);
        return true;
      }

      throw new Error(response.message || 'Failed to unshare agent');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error unsharing agent';
      logger.error('Error unsharing agent:', err);
      setError(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const importAgent = useCallback(async (shareToken: string): Promise<UserAgentInstance | null> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.importAgent(shareToken);

      if (response.success && response.instance) {
        logger.info(`Imported agent: ${response.instance.agent_name}`);
        return response.instance;
      }

      throw new Error(response.message || 'Failed to import agent');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error importing agent';
      logger.error('Error importing agent:', err);
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    shareAgent,
    unshareAgent,
    importAgent,
  };
}

// ============================================================================
// useAgentMarketplace - Browse and preview marketplace agents
// ============================================================================

interface UseAgentMarketplaceReturn {
  agents: MarketplaceAgent[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  error: string | null;
  browseMarketplace: (filters?: MarketplaceFilters) => Promise<void>;
  previewAgent: (shareToken: string) => Promise<SharedAgentPreviewResponse | null>;
  setPage: (page: number) => void;
}

/**
 * Hook for browsing the agent marketplace
 * Displays publicly shared agents from all users
 */
export function useAgentMarketplace(): UseAgentMarketplaceReturn {
  const [agents, setAgents] = useState<MarketplaceAgent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isLoadingRef = useRef(false);

  const browseMarketplace = useCallback(async (filters?: MarketplaceFilters) => {
    if (isLoadingRef.current) return;

    isLoadingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.browseMarketplace({
        ...filters,
        page: filters?.page || page,
        page_size: filters?.page_size || pageSize,
      });

      if (response.success && response.agents) {
        setAgents(response.agents);
        setTotal(response.total || 0);
        setPage(response.page || 1);
        setPageSize(response.page_size || 20);
        logger.info(`Loaded ${response.agents.length} marketplace agents`);
      } else {
        throw new Error(response.message || 'Failed to browse marketplace');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error browsing marketplace';
      logger.error('Error browsing marketplace:', err);
      setError(errorMessage);
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  }, [page, pageSize]);

  const previewAgent = useCallback(async (shareToken: string): Promise<SharedAgentPreviewResponse | null> => {
    try {
      const response: any = await agentManagementApiV2.previewSharedAgent(shareToken);

      if (response.success) {
        return response as SharedAgentPreviewResponse;
      }

      throw new Error(response.message || 'Failed to preview agent');
    } catch (err) {
      logger.error('Error previewing agent:', err);
      return null;
    }
  }, []);

  // Auto-load marketplace on mount
  useEffect(() => {
    browseMarketplace();
  }, [browseMarketplace]);

  return {
    agents,
    total,
    page,
    pageSize,
    loading,
    error,
    browseMarketplace,
    previewAgent,
    setPage,
  };
}

// ============================================================================
// useAgentAnalytics - Usage statistics and analytics
// ============================================================================

interface UseAgentAnalyticsReturn {
  userStats: UserUsageStats | null;
  popularAgents: PopularAgentStats[];
  loading: boolean;
  error: string | null;
  loadUserStats: () => Promise<void>;
  loadPopularAgents: () => Promise<void>;
}

/**
 * Hook for agent usage analytics
 * Provides user statistics and popular agent insights
 */
export function useAgentAnalytics(): UseAgentAnalyticsReturn {
  const [userStats, setUserStats] = useState<UserUsageStats | null>(null);
  const [popularAgents, setPopularAgents] = useState<PopularAgentStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadUserStats = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.getUserStats();

      if (response.success && response.user_stats) {
        setUserStats(response.user_stats);
        logger.info('Loaded user agent statistics');
      } else {
        throw new Error(response.message || 'Failed to load user stats');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error loading user stats';
      logger.error('Error loading user stats:', err);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPopularAgents = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.getPopularAgents();

      if (response.success && response.popular_agents) {
        setPopularAgents(response.popular_agents);
        logger.info('Loaded popular agent statistics');
      } else {
        throw new Error(response.message || 'Failed to load popular agents');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error loading popular agents';
      logger.error('Error loading popular agents:', err);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    userStats,
    popularAgents,
    loading,
    error,
    loadUserStats,
    loadPopularAgents,
  };
}
