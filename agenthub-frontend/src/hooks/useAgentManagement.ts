/**
 * Agent Management Custom Hooks
 *
 * Provides React hooks for interacting with the User-Specific Agent System.
 * These hooks follow the project's custom hooks pattern (NOT React Query).
 *
 * @module hooks/useAgentManagement
 * @version 1.0.0
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { agentManagementApiV2 } from '../services/apiV2';
import logger from '../utils/logger';
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
  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isLoadingRef = useRef(false);

  const loadTemplates = useCallback(async () => {
    if (isLoadingRef.current) return;

    isLoadingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.listTemplates();

      if (response.success && response.templates) {
        setTemplates(response.templates);
        logger.info(`Loaded ${response.templates.length} agent templates`);
      } else {
        throw new Error(response.message || 'Failed to load templates');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error loading templates';
      logger.error('Error loading agent templates:', err);
      setError(errorMessage);
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  }, []);

  const getTemplateBySlug = useCallback((slug: string) => {
    return templates.find(t => t.slug === slug);
  }, [templates]);

  // Auto-load templates on mount
  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  return {
    templates,
    loading,
    error,
    loadTemplates,
    getTemplateBySlug,
  };
}

// ============================================================================
// useUserAgentInstances - Manage user's agent instances
// ============================================================================

interface UseUserAgentInstancesReturn {
  instances: UserAgentInstance[];
  loading: boolean;
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
 * Hook for managing user's agent instances
 * Handles CRUD operations for customized agent instances
 */
export function useUserAgentInstances(): UseUserAgentInstancesReturn {
  const [instances, setInstances] = useState<UserAgentInstance[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isLoadingRef = useRef(false);

  const loadInstances = useCallback(async () => {
    if (isLoadingRef.current) return;

    isLoadingRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.listUserInstances();

      if (response.success && response.instances) {
        setInstances(response.instances);
        logger.info(`Loaded ${response.instances.length} agent instances`);
      } else {
        throw new Error(response.message || 'Failed to load instances');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error loading instances';
      logger.error('Error loading agent instances:', err);
      setError(errorMessage);
    } finally {
      setLoading(false);
      isLoadingRef.current = false;
    }
  }, []);

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

  const createInstance = useCallback(async (data: CreateInstanceRequest): Promise<UserAgentInstance | null> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.createInstance(data);

      // Backend returns the instance directly (not wrapped in {success, instance})
      if (response && response.id) {
        // Add to local state
        setInstances(prev => [...prev, response]);
        logger.info(`Created instance: ${response.agent_name}`);
        return response;
      }

      throw new Error('Failed to create instance - invalid response');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error creating instance';
      logger.error('Error creating instance:', err);
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const bulkCreateInstances = useCallback(async (): Promise<UserAgentInstance[]> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.bulkCreateInstances();

      // Backend returns array of instances directly
      if (Array.isArray(response)) {
        // Add all new instances to local state
        setInstances(prev => [...prev, ...response]);
        logger.info(`Bulk created ${response.length} instances`);
        return response;
      }

      throw new Error('Failed to bulk create instances - invalid response');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error bulk creating instances';
      logger.error('Error bulk creating instances:', err);
      setError(errorMessage);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const updateInstance = useCallback(async (
    instanceId: string,
    data: UpdateInstanceRequest
  ): Promise<UserAgentInstance | null> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.updateInstance(instanceId, data);

      if (response.success && response.instance) {
        // Update in local state
        setInstances(prev => prev.map(inst =>
          inst.id === instanceId ? response.instance : inst
        ));
        logger.info(`Updated instance: ${instanceId}`);
        return response.instance;
      }

      throw new Error(response.message || 'Failed to update instance');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error updating instance';
      logger.error('Error updating instance:', err);
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteInstance = useCallback(async (instanceId: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const response: any = await agentManagementApiV2.deleteInstance(instanceId);

      if (response.success) {
        // Remove from local state
        setInstances(prev => prev.filter(inst => inst.id !== instanceId));
        logger.info(`Deleted instance: ${instanceId}`);
        return true;
      }

      throw new Error(response.message || 'Failed to delete instance');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error deleting instance';
      logger.error('Error deleting instance:', err);
      setError(errorMessage);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshInstance = useCallback(async (instanceId: string) => {
    const instance = await getInstance(instanceId);
    if (instance) {
      setInstances(prev => prev.map(inst =>
        inst.id === instanceId ? instance : inst
      ));
    }
  }, [getInstance]);

  const toggleEnabled = useCallback(async (instanceId: string, enabled: boolean): Promise<boolean> => {
    try {
      const response: any = await agentManagementApiV2.updateInstance(instanceId, {
        is_enabled: enabled,
      });

      // Backend returns the instance directly (not wrapped in {success, instance})
      if (response && response.id) {
        // Update in local state
        setInstances(prev => prev.map(inst =>
          inst.id === instanceId ? response : inst
        ));
        logger.info(`${enabled ? 'Enabled' : 'Disabled'} agent: ${instanceId}`);
        return true;
      }

      throw new Error('Failed to toggle enabled status - invalid response');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error toggling enabled status';
      logger.error('Error toggling enabled status:', err);
      setError(errorMessage);
      return false;
    }
  }, []);

  // Auto-load instances on mount
  useEffect(() => {
    loadInstances();
  }, [loadInstances]);

  return {
    instances,
    loading,
    error,
    loadInstances,
    getInstance,
    createInstance,
    bulkCreateInstances,
    updateInstance,
    deleteInstance,
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
