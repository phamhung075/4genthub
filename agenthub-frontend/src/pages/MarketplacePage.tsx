/**
 * Agent Marketplace Page
 *
 * Browse and import publicly shared agents from the community.
 * Features: search, filtering, sorting, pagination, and one-click import.
 *
 * @module pages/MarketplacePage
 * @version 1.0.0
 */

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  TrendingUp,
  Clock,
  User,
  Download,
  Sparkles,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Eye,
  X,
  Wrench,
  Code,
  FileText,
  Copy,
  Settings2,
  ListChecks,
  FileOutput,
} from 'lucide-react';
import { useAgentMarketplace, useAgentSharing } from '../hooks/useAgentManagement';
import type { MarketplaceAgent, MarketplaceFilters, SharedAgentPreviewResponse } from '../types/agentTypes';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Separator } from '../components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import logger from '../utils/logger';

/**
 * Agent Marketplace Page Component
 * Main page for browsing and importing public shared agents
 */
export const MarketplacePage: React.FC = () => {
  const { agents, total, page, pageSize, loading, error, browseMarketplace, setPage } =
    useAgentMarketplace();
  const { importAgent, loading: importing, error: importError } = useAgentSharing();

  // Local state for filtering and sorting
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'recent' | 'popular'>('recent');
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  // State for agent details dialog
  const [selectedAgent, setSelectedAgent] = useState<MarketplaceAgent | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Extract unique categories from agents
  const categories = useMemo(() => {
    const cats = new Set<string>();
    agents.forEach(agent => {
      // Extract category from template slug (e.g., 'coding-agent' -> 'coding')
      const category = agent.template_slug.split('-')[0];
      cats.add(category);
    });
    return Array.from(cats).sort();
  }, [agents]);

  // Build filters for API call
  const currentFilters: MarketplaceFilters = useMemo(
    () => ({
      search: searchQuery || undefined,
      category: selectedCategory || undefined,
      sort: sortBy,
      page,
      page_size: pageSize,
    }),
    [searchQuery, selectedCategory, sortBy, page, pageSize]
  );

  // Load marketplace agents when filters change
  useEffect(() => {
    browseMarketplace(currentFilters);
  }, [currentFilters, browseMarketplace]);

  // Handle import
  const handleImport = useCallback(
    async (agent: MarketplaceAgent) => {
      try {
        setImportSuccess(null);
        const imported = await importAgent(agent.share_token);

        if (imported) {
          setImportSuccess(
            `Successfully imported "${agent.agent_name}" from ${agent.creator_display_name}`
          );
          // Clear success message after 5 seconds
          setTimeout(() => setImportSuccess(null), 5000);
        }
      } catch (err) {
        logger.error('Error importing agent:', err);
      }
    },
    [importAgent]
  );

  // Handle view details
  const handleViewDetails = useCallback((agent: MarketplaceAgent) => {
    setSelectedAgent(agent);
    setIsDialogOpen(true);
  }, []);

  // Calculate pagination
  const totalPages = Math.ceil(total / pageSize);
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold tracking-tight">Agent Marketplace</h1>
        <p className="text-muted-foreground mt-2">
          Discover and import agents customized by the community
        </p>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Search Bar */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search agents..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Sort Toggle */}
            <div className="flex items-center gap-2">
              <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
              <div className="flex gap-2">
                <Button
                  variant={sortBy === 'recent' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('recent')}
                  className="gap-2"
                >
                  <Clock className="h-4 w-4" />
                  Recent
                </Button>
                <Button
                  variant={sortBy === 'popular' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSortBy('popular')}
                  className="gap-2"
                >
                  <TrendingUp className="h-4 w-4" />
                  Popular
                </Button>
              </div>
            </div>
          </div>

          {/* Category Filter */}
          {categories.length > 0 && (
            <>
              <Separator className="my-4" />
              <div className="flex items-center gap-2 flex-wrap">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Button
                  variant={selectedCategory === null ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedCategory(null)}
                >
                  All Categories
                </Button>
                {categories.map(category => (
                  <Button
                    key={category}
                    variant={selectedCategory === category ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedCategory(category)}
                    className="capitalize"
                  >
                    {category}
                  </Button>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Success Message */}
      {importSuccess && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">{importSuccess}</AlertDescription>
        </Alert>
      )}

      {/* Import Error */}
      {importError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{importError}</AlertDescription>
        </Alert>
      )}

      {/* Load Error */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

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
      {!loading && agents.length > 0 && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map(agent => (
              <MarketplaceAgentCard
                key={agent.instance_id}
                agent={agent}
                onImport={handleImport}
                onViewDetails={handleViewDetails}
                importing={importing}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Showing {(page - 1) * pageSize + 1} to{' '}
                    {Math.min(page * pageSize, total)} of {total} agents
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={!hasPrevPage || loading}
                      className="gap-2"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>

                    <div className="flex items-center gap-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        const pageNum = i + 1;
                        return (
                          <Button
                            key={pageNum}
                            variant={page === pageNum ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setPage(pageNum)}
                            disabled={loading}
                            className="w-10"
                          >
                            {pageNum}
                          </Button>
                        );
                      })}
                      {totalPages > 5 && (
                        <>
                          <span className="px-2">...</span>
                          <Button
                            variant={page === totalPages ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setPage(totalPages)}
                            disabled={loading}
                            className="w-10"
                          >
                            {totalPages}
                          </Button>
                        </>
                      )}
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={!hasNextPage || loading}
                      className="gap-2"
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Empty State */}
      {!loading && agents.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold mb-2">No agents found</p>
            <p className="text-sm text-muted-foreground mb-4">
              {searchQuery || selectedCategory
                ? 'Try adjusting your filters or search terms'
                : 'No public agents available in the marketplace yet'}
            </p>
            {(searchQuery || selectedCategory) && (
              <Button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory(null);
                }}
              >
                Clear Filters
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Agent Details Dialog */}
      <AgentDetailDialog
        agent={selectedAgent}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        onImport={handleImport}
        importing={importing}
      />
    </div>
  );
};

/**
 * Agent Detail Dialog Component
 * Shows full agent information in a modal dialog
 */
interface AgentDetailDialogProps {
  agent: MarketplaceAgent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (agent: MarketplaceAgent) => void;
  importing: boolean;
}

const AgentDetailDialog: React.FC<AgentDetailDialogProps> = ({
  agent,
  open,
  onOpenChange,
  onImport,
  importing,
}) => {
  const { previewAgent } = useAgentMarketplace();
  const [preview, setPreview] = useState<SharedAgentPreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Load full preview when dialog opens
  useEffect(() => {
    const loadPreview = async () => {
      if (!open || !agent) {
        setPreview(null);
        setPreviewError(null);
        return;
      }

      setLoadingPreview(true);
      setPreviewError(null);

      try {
        const data = await previewAgent(agent.share_token);
        if (data) {
          setPreview(data);
        } else {
          setPreviewError('Failed to load agent preview');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error loading preview';
        setPreviewError(errorMessage);
        logger.error('Error loading agent preview:', err);
      } finally {
        setLoadingPreview(false);
      }
    };

    loadPreview();
  }, [open, agent, previewAgent]);

  if (!agent) return null;

  const formattedDate = new Date(agent.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const category = agent.template_slug.split('-')[0];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-7xl max-h-[95vh] overflow-y-auto">
        {/* Enhanced Header - Matches My Agents */}
        <DialogHeader className="pb-6 border-b">
          <DialogTitle className="text-3xl font-bold flex items-center gap-3">
            <Sparkles className="h-7 w-7 text-primary" />
            {agent.agent_name}
          </DialogTitle>
          <DialogDescription className="flex flex-wrap items-center gap-2 text-base pt-2">
            <Badge variant="secondary" className="capitalize text-sm">
              {category}
            </Badge>
            <span className="flex items-center gap-1 text-muted-foreground">
              <User className="h-4 w-4" />
              Created by {agent.creator_display_name}
            </span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground">{formattedDate}</span>
          </DialogDescription>
        </DialogHeader>

        {/* Loading State */}
        {loadingPreview && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Error State */}
        {previewError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{previewError}</AlertDescription>
          </Alert>
        )}

        {/* Enhanced Content - Matches My Agents */}
        {!loadingPreview && !previewError && preview && (
          <div className="space-y-8 py-6">
            {/* Stats Cards - 3-column grid with gradient backgrounds */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="p-6 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
                <div className="flex items-center gap-3 mb-2">
                  <TrendingUp className="h-6 w-6 text-primary" />
                  <h3 className="font-semibold text-lg">Usage Count</h3>
                </div>
                <p className="text-4xl font-bold text-primary">{agent.usage_count}</p>
              </div>

              <div className="p-6 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20">
                <div className="flex items-center gap-3 mb-2">
                  <Wrench className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  <h3 className="font-semibold text-lg">Tools</h3>
                </div>
                <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">
                  {preview.configuration_preview.tools.length}
                </p>
              </div>

              <div className="p-6 rounded-lg bg-gradient-to-br from-purple-500/10 to-purple-500/5 border border-purple-500/20">
                <div className="flex items-center gap-3 mb-2">
                  <Code className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  <h3 className="font-semibold text-lg">Template</h3>
                </div>
                <p className="text-lg font-semibold text-purple-600 dark:text-purple-400 truncate">
                  {agent.template_slug}
                </p>
              </div>
            </div>

            {/* Description */}
            {agent.customizations_summary && (
              <div className="space-y-3">
                <h3 className="font-bold text-xl flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  Description
                </h3>
                <p className="text-base text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {agent.customizations_summary}
                </p>
              </div>
            )}

            {/* System Prompt with Copy button */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-xl flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  System Prompt
                </h3>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(preview.configuration_preview.system_prompt);
                  }}
                  className="gap-2"
                >
                  <Copy className="h-4 w-4" />
                  Copy
                </Button>
              </div>
              <div className="rounded-lg border bg-muted/50 p-6">
                <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed">
                  {preview.configuration_preview.system_prompt}
                </pre>
              </div>
            </div>

            {/* Tools - Full width with badges */}
            <div className="space-y-3">
              <h3 className="font-bold text-xl flex items-center gap-2">
                <Wrench className="h-5 w-5 text-primary" />
                Tools ({preview.configuration_preview.tools.length})
              </h3>
              <div className="rounded-lg border bg-muted/50 p-6">
                <div className="flex flex-wrap gap-2">
                  {preview.configuration_preview.tools.map((tool, idx) => (
                    <Badge key={idx} variant="secondary" className="text-sm px-3 py-1 font-mono">
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            {/* Capabilities - Full width with key-value display */}
            <div className="space-y-3">
              <h3 className="font-bold text-xl flex items-center gap-2">
                <Settings2 className="h-5 w-5 text-primary" />
                Capabilities
              </h3>
              <div className="rounded-lg border bg-muted/50 p-6">
                <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed">
                  {JSON.stringify(preview.configuration_preview.capabilities, null, 2)}
                </pre>
              </div>
            </div>

            {/* Rules - Full width with numbered list */}
            {preview.configuration_preview.rules && preview.configuration_preview.rules.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-bold text-xl flex items-center gap-2">
                  <ListChecks className="h-5 w-5 text-primary" />
                  Rules ({preview.configuration_preview.rules.length})
                </h3>
                <div className="rounded-lg border bg-muted/50 p-6">
                  <ol className="space-y-3 list-decimal list-inside">
                    {preview.configuration_preview.rules.map((rule, idx) => (
                      <li key={idx} className="text-base leading-relaxed">
                        {rule}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            )}

            {/* Output Format */}
            {preview.configuration_preview.output_format && (
              <div className="space-y-3">
                <h3 className="font-bold text-xl flex items-center gap-2">
                  <FileOutput className="h-5 w-5 text-primary" />
                  Output Format
                </h3>
                <div className="rounded-lg border bg-muted/50 p-6">
                  <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed">
                    {preview.configuration_preview.output_format}
                  </pre>
                </div>
              </div>
            )}

            <Separator />

            {/* Import Action */}
            <div className="flex gap-3 pt-4">
              <Button
                onClick={() => onImport(agent)}
                disabled={importing || !preview.can_import}
                className="flex-1 gap-2"
                size="lg"
              >
                {importing ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Importing Agent...
                  </>
                ) : (
                  <>
                    <Download className="h-5 w-5" />
                    Import This Agent
                  </>
                )}
              </Button>
              <Button
                onClick={() => onOpenChange(false)}
                variant="outline"
                size="lg"
                className="gap-2"
              >
                <X className="h-5 w-5" />
                Close
              </Button>
            </div>

            {/* Import Warning */}
            {!preview.can_import && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {preview.message || 'This agent cannot be imported at this time.'}
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

/**
 * Marketplace Agent Card Component
 * Individual card for each marketplace agent
 */
interface MarketplaceAgentCardProps {
  agent: MarketplaceAgent;
  onImport: (agent: MarketplaceAgent) => void;
  onViewDetails: (agent: MarketplaceAgent) => void;
  importing: boolean;
}

const MarketplaceAgentCard: React.FC<MarketplaceAgentCardProps> = ({
  agent,
  onImport,
  onViewDetails,
  importing,
}) => {
  const formattedDate = new Date(agent.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  // Extract category from template slug
  const category = agent.template_slug.split('-')[0];

  return (
    <Card className="group hover:shadow-lg transition-all hover:border-primary/50">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {agent.agent_name}
              <Badge variant="secondary" className="gap-1 capitalize">
                {category}
              </Badge>
            </CardTitle>
            <CardDescription className="mt-2 flex items-center gap-2">
              <User className="h-3 w-3" />
              {agent.creator_display_name}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Customizations Summary */}
        <div className="text-sm text-muted-foreground line-clamp-3">
          {agent.customizations_summary || 'No customization details provided'}
        </div>

        <Separator />

        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            {agent.usage_count} {agent.usage_count === 1 ? 'use' : 'uses'}
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formattedDate}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={() => onViewDetails(agent)}
            variant="outline"
            className="flex-1 gap-2"
          >
            <Eye className="h-4 w-4" />
            View Details
          </Button>
          <Button
            onClick={() => onImport(agent)}
            disabled={importing}
            className="flex-1 gap-2"
          >
            {importing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Import
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default MarketplacePage;
