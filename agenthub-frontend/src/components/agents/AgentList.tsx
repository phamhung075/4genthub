/**
 * Agent List Component
 *
 * Displays user's agent instances with cards showing customization status,
 * visibility, and creator attribution. Supports filtering and search.
 *
 * @module components/agents/AgentList
 * @version 1.0.0
 */

import React, { useState, useMemo } from 'react';
import {
  Settings,
  Share2,
  Lock,
  Globe,
  Star,
  Search,
  Filter,
  Plus,
  User,
  Sparkles,
} from 'lucide-react';
import { useUserAgentInstances } from '../../hooks/useAgentManagement';
import type { UserAgentInstance } from '../../types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import logger from '../../utils/logger';

interface AgentListProps {
  onAgentSelect?: (agent: UserAgentInstance) => void;
  onConfigureAgent?: (agent: UserAgentInstance) => void;
  onShareAgent?: (agent: UserAgentInstance) => void;
  onCreateNew?: () => void;
}

/**
 * Agent List Component
 * Displays and manages user's agent instances
 */
export const AgentList: React.FC<AgentListProps> = ({
  onAgentSelect,
  onConfigureAgent,
  onShareAgent,
  onCreateNew,
}) => {
  const { instances, loading, error, loadInstances } = useUserAgentInstances();

  // Local state for filtering and search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showCustomizedOnly, setShowCustomizedOnly] = useState(false);

  // Extract unique categories from instances
  const categories = useMemo(() => {
    const cats = new Set<string>();
    instances.forEach(instance => {
      // Extract category from template slug (e.g., 'coding-agent' -> 'coding')
      const category = instance.agent_name.split('-')[0];
      cats.add(category);
    });
    return Array.from(cats).sort();
  }, [instances]);

  // Filter instances based on search and filters
  const filteredInstances = useMemo(() => {
    return instances.filter(instance => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          instance.agent_name.toLowerCase().includes(query) ||
          instance.system_prompt?.toLowerCase().includes(query);
        if (!matchesSearch) return false;
      }

      // Category filter
      if (selectedCategory) {
        const category = instance.agent_name.split('-')[0];
        if (category !== selectedCategory) return false;
      }

      // Customization filter
      if (showCustomizedOnly && !instance.is_customized) {
        return false;
      }

      return true;
    });
  }, [instances, searchQuery, selectedCategory, showCustomizedOnly]);

  // Handle errors
  if (error) {
    return (
      <div className="p-6">
        <Card className="border-red-500">
          <CardHeader>
            <CardTitle className="text-red-500">Error Loading Agents</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={loadInstances}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">My Agents</h2>
          <p className="text-muted-foreground">
            {instances.length} agent{instances.length !== 1 ? 's' : ''} configured
          </p>
        </div>
        {onCreateNew && (
          <Button onClick={onCreateNew} className="gap-2">
            <Plus className="h-4 w-4" />
            Create New Agent
          </Button>
        )}
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All
            </Button>
            {categories.map(category => (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </Button>
            ))}
          </div>
        </div>

        {/* Customized Only Toggle */}
        <Button
          variant={showCustomizedOnly ? 'default' : 'outline'}
          size="sm"
          onClick={() => setShowCustomizedOnly(!showCustomizedOnly)}
          className="gap-2"
        >
          <Sparkles className="h-4 w-4" />
          Customized
        </Button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-6 w-3/4 rounded bg-muted" />
                <div className="h-4 w-1/2 rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-4 w-full rounded bg-muted" />
                  <div className="h-4 w-2/3 rounded bg-muted" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Agent Cards Grid */}
      {!loading && filteredInstances.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredInstances.map(instance => (
            <AgentCard
              key={instance.id}
              instance={instance}
              onSelect={onAgentSelect}
              onConfigure={onConfigureAgent}
              onShare={onShareAgent}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredInstances.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <User className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold mb-2">No agents found</p>
            <p className="text-sm text-muted-foreground mb-4">
              {searchQuery || selectedCategory || showCustomizedOnly
                ? 'Try adjusting your filters'
                : 'Get started by creating your first agent'}
            </p>
            {onCreateNew && !searchQuery && !selectedCategory && (
              <Button onClick={onCreateNew}>Create Your First Agent</Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

/**
 * Agent Card Component
 * Individual card for each agent instance
 */
interface AgentCardProps {
  instance: UserAgentInstance;
  onSelect?: (instance: UserAgentInstance) => void;
  onConfigure?: (instance: UserAgentInstance) => void;
  onShare?: (instance: UserAgentInstance) => void;
}

const AgentCard: React.FC<AgentCardProps> = ({
  instance,
  onSelect,
  onConfigure,
  onShare,
}) => {
  const isPublic = instance.visibility === 'public';
  const isCustomized = instance.is_customized;

  // Format dates
  const createdDate = new Date(instance.created_at).toLocaleDateString();
  const lastUsedDate = instance.last_used_at
    ? new Date(instance.last_used_at).toLocaleDateString()
    : 'Never';

  return (
    <Card
      className="group cursor-pointer transition-all hover:shadow-lg hover:border-primary/50"
      onClick={() => onSelect?.(instance)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {instance.agent_name}
              {isCustomized && (
                <Badge variant="secondary" className="gap-1">
                  <Sparkles className="h-3 w-3" />
                  Customized
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="mt-1">
              {instance.tools?.slice(0, 3).join(', ')}
              {instance.tools && instance.tools.length > 3 && '...'}
            </CardDescription>
          </div>

          {/* Visibility Badge */}
          <div className="ml-2">
            {isPublic ? (
              <Badge variant="default" className="gap-1">
                <Globe className="h-3 w-3" />
                Public
              </Badge>
            ) : (
              <Badge variant="outline" className="gap-1">
                <Lock className="h-3 w-3" />
                Private
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* System Prompt Preview */}
        <div className="text-sm text-muted-foreground line-clamp-2">
          {instance.system_prompt?.substring(0, 150)}
          {instance.system_prompt && instance.system_prompt.length > 150 && '...'}
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Star className="h-3 w-3" />
            {instance.usage_count || 0} uses
          </div>
          <div>
            Created {createdDate}
          </div>
        </div>

        {/* Last Used */}
        {instance.last_used_at && (
          <div className="text-xs text-muted-foreground">
            Last used: {lastUsedDate}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2 border-t">
          {onConfigure && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-2"
              onClick={(e) => {
                e.stopPropagation();
                onConfigure(instance);
              }}
            >
              <Settings className="h-4 w-4" />
              Configure
            </Button>
          )}

          {onShare && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1 gap-2"
              onClick={(e) => {
                e.stopPropagation();
                onShare(instance);
              }}
            >
              <Share2 className="h-4 w-4" />
              Share
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default AgentList;
