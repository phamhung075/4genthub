/**
 * My Agents Page
 *
 * View and manage user's personal agent instances.
 * Features: search, filtering, CRUD operations, usage stats.
 *
 * @module pages/MyAgentsPage
 * @version 1.0.0
 */

import React, { useState, useMemo, useEffect } from 'react';
import {
  Search,
  Filter,
  Plus,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Eye,
  Edit,
  Trash2,
  X,
  Calendar,
  Activity,
  Sparkles,
} from 'lucide-react';
import { useUserAgentInstances, useAgentTemplates } from '../hooks/useAgentManagement';
import { useNavigate } from 'react-router-dom';
import type { UserAgentInstance, AgentTemplate, UpdateInstanceRequest } from '../types/agentTypes';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Separator } from '../components/ui/separator';
import { Checkbox } from '../components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import logger from '../utils/logger';
import { useAuth } from '../contexts/AuthContext';
import { useWebSocket } from '../hooks/useWebSocketV2';
import { useRealtimeSync } from '../hooks/useRealtimeSync';
import { ENABLE_MARKETPLACE } from '../config/environment';

/**
 * My Agents Page Component
 * Displays user's personal agent instances with management capabilities
 */
export const MyAgentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, tokens } = useAuth();

  // WebSocket integration for real-time updates
  const webSocketClient = useWebSocket(user?.id || '', tokens?.access_token || '');
  useRealtimeSync(webSocketClient.client, true);

  const { instances, isLoading: loading, error, loadInstances, deleteInstance, createInstance, bulkCreateInstances, toggleEnabled, updateInstance } = useUserAgentInstances();
  const { templates, loading: templatesLoading } = useAgentTemplates();

  // Local state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedVisibility, setSelectedVisibility] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);
  const [bulkCreateSuccess, setBulkCreateSuccess] = useState<string | null>(null);
  const [bulkCreating, setBulkCreating] = useState(false);
  const [selectedInstance, setSelectedInstance] = useState<UserAgentInstance | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplate | null>(null);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [instanceToDelete, setInstanceToDelete] = useState<UserAgentInstance | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [instanceToEdit, setInstanceToEdit] = useState<UserAgentInstance | null>(null);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Edit form state (moved to top level to comply with React Rules of Hooks)
  const [formData, setFormData] = useState({
    agent_name: '',
    system_prompt: '',
    tools: [] as string[],
    capabilities: '{}',
    rules: [] as string[],
    output_format: '',
    visibility: 'private' as 'private' | 'public',
    is_enabled: true,
  });
  const [newTool, setNewTool] = useState('');
  const [newRule, setNewRule] = useState('');
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);

  // Update form data when instanceToEdit changes
  useEffect(() => {
    if (instanceToEdit) {
      // Normalize tools and rules to always be string arrays (handle both string and object formats)
      const normalizeToStringArray = (arr: any[]): string[] => {
        if (!arr) return [];
        return arr.map(item => {
          if (typeof item === 'string') return item;
          if (typeof item === 'object') return item?.name || item?.content || JSON.stringify(item);
          return String(item);
        });
      };

      // Normalize text fields if they're objects
      const normalizeTextField = (value: any): string => {
        if (!value) return '';
        if (typeof value === 'string') return value;
        if (typeof value === 'object') {
          // Try to extract text content from object
          return value.content || value.text || value.format || value.prompt || JSON.stringify(value, null, 2);
        }
        return String(value);
      };

      setFormData({
        agent_name: typeof instanceToEdit.agent_name === 'string' ? instanceToEdit.agent_name : String(instanceToEdit.agent_name || ''),
        system_prompt: normalizeTextField(instanceToEdit.system_prompt),
        tools: normalizeToStringArray(instanceToEdit.tools || []),
        capabilities: JSON.stringify(instanceToEdit.capabilities || {}, null, 2),
        rules: normalizeToStringArray(instanceToEdit.rules || []),
        output_format: normalizeTextField(instanceToEdit.output_format),
        visibility: instanceToEdit.visibility,
        is_enabled: instanceToEdit.is_enabled,
      });
      setCapabilitiesError(null);
    }
  }, [instanceToEdit]);

  // Filter instances
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

      // Visibility filter
      // For 'default' filter, don't show instances (only templates are shown)
      if (selectedVisibility === 'default') {
        return false;
      } else if (selectedVisibility && instance.visibility !== selectedVisibility) {
        return false;
      }

      return true;
    });
  }, [instances, searchQuery, selectedVisibility]);

  // Filter templates for Default tab
  const filteredTemplates = useMemo(() => {
    // Only show templates when Default filter is active
    if (selectedVisibility !== 'default') {
      return [];
    }

    return templates.filter(template => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
          template.name.toLowerCase().includes(query) ||
          template.description?.toLowerCase().includes(query) ||
          template.category?.toLowerCase().includes(query);
        if (!matchesSearch) return false;
      }

      return true;
    });
  }, [templates, searchQuery, selectedVisibility]);

  // Create set of template IDs that already have instances
  const existingTemplateIds = useMemo(() => {
    return new Set(instances.map(instance => instance.template_id));
  }, [instances]);

  // Handle view details for instance
  const handleViewDetails = (instance: UserAgentInstance) => {
    setSelectedInstance(instance);
    setSelectedTemplate(null);
    setIsDetailsDialogOpen(true);
  };

  // Handle view details for template
  const handleViewTemplateDetails = (template: AgentTemplate) => {
    setSelectedTemplate(template);
    setSelectedInstance(null);
    setIsDetailsDialogOpen(true);
  };

  // Handle delete confirmation
  const handleDeleteClick = (instance: UserAgentInstance) => {
    setInstanceToDelete(instance);
    setIsDeleteDialogOpen(true);
  };

  // Handle instantiate template
  const handleInstantiateTemplate = async (template: AgentTemplate) => {
    setCreating(true);
    setCreateSuccess(null);
    setIsDetailsDialogOpen(false);

    try {
      const instance = await createInstance({
        template_slug: template.slug,
      });

      if (instance) {
        setCreateSuccess(`Created "${template.name}" instance successfully!`);
        // Clear success message after 5 seconds
        setTimeout(() => setCreateSuccess(null), 5000);
        // Reload instances to show the new one
        await loadInstances();
      }
    } catch (err) {
      logger.error('Error creating instance:', err);
    } finally {
      setCreating(false);
    }
  };

  // Handle bulk create all templates
  const handleBulkCreate = async () => {
    setBulkCreating(true);
    setBulkCreateSuccess(null);

    try {
      const createdInstances = await bulkCreateInstances();

      if (createdInstances && createdInstances.length > 0) {
        setBulkCreateSuccess(`Successfully created ${createdInstances.length} agent instance${createdInstances.length > 1 ? 's' : ''}!`);
        // Clear success message after 5 seconds
        setTimeout(() => setBulkCreateSuccess(null), 5000);
        // Reload instances to show the new ones
        await loadInstances();
      } else {
        setBulkCreateSuccess('All agent instances already exist!');
        setTimeout(() => setBulkCreateSuccess(null), 5000);
      }
    } catch (err) {
      logger.error('Error bulk creating instances:', err);
    } finally {
      setBulkCreating(false);
    }
  };

  // Handle delete execution
  const handleDeleteConfirm = async () => {
    if (!instanceToDelete) return;

    setDeleting(true);
    try {
      const success = await deleteInstance(instanceToDelete.id);

      if (success) {
        setDeleteSuccess(`Deleted "${instanceToDelete.agent_name}" successfully!`);
        setIsDeleteDialogOpen(false);
        setInstanceToDelete(null);

        // Clear success message after 5 seconds
        setTimeout(() => setDeleteSuccess(null), 5000);
      }
    } catch (err) {
      logger.error('Error deleting instance:', err);
    } finally {
      setDeleting(false);
    }
  };

  // Handle edit click
  const handleEditClick = (instance: UserAgentInstance) => {
    setInstanceToEdit(instance);
    setEditError(null);
    setIsEditDialogOpen(true);
  };

  // Handle edit save
  const handleEditSave = async (data: UpdateInstanceRequest) => {
    if (!instanceToEdit) return;

    setSaving(true);
    setEditError(null);

    try {
      const updated = await updateInstance(instanceToEdit.id, data);

      if (updated) {
        setIsEditDialogOpen(false);
        setInstanceToEdit(null);
        setCreateSuccess(`Updated "${updated.agent_name}" successfully!`);
        setTimeout(() => setCreateSuccess(null), 5000);
        await loadInstances();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error updating agent';
      logger.error('Error updating agent:', err);
      setEditError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  // Edit form handlers (moved to top level to comply with React Rules of Hooks)
  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (field === 'capabilities') {
      setCapabilitiesError(null);
    }
  };

  const handleAddTool = () => {
    if (newTool.trim() && !formData.tools.includes(newTool.trim())) {
      setFormData(prev => ({ ...prev, tools: [...prev.tools, newTool.trim()] }));
      setNewTool('');
    }
  };

  const handleRemoveTool = (index: number) => {
    setFormData(prev => ({
      ...prev,
      tools: prev.tools.filter((_, i) => i !== index)
    }));
  };

  const handleAddRule = () => {
    if (newRule.trim()) {
      setFormData(prev => ({ ...prev, rules: [...prev.rules, newRule.trim()] }));
      setNewRule('');
    }
  };

  const handleRemoveRule = (index: number) => {
    setFormData(prev => ({
      ...prev,
      rules: prev.rules.filter((_, i) => i !== index)
    }));
  };

  const handleEditFormSave = () => {
    // Validate capabilities JSON
    let parsedCapabilities;
    try {
      parsedCapabilities = JSON.parse(formData.capabilities);
    } catch (err) {
      setCapabilitiesError('Invalid JSON format for capabilities');
      return;
    }

    // Generate or use existing share_token when visibility is public
    let shareToken: string | null = null;
    if (formData.visibility === 'public') {
      if (instanceToEdit?.share_token) {
        // Use existing token if already exists
        shareToken = instanceToEdit.share_token;
      } else {
        // Generate new 64-character random token
        shareToken = Array.from(crypto.getRandomValues(new Uint8Array(32)))
          .map(b => b.toString(16).padStart(2, '0'))
          .join('');
      }
    }

    // Prepare update data
    const updateData: UpdateInstanceRequest = {
      agent_name: formData.agent_name,
      system_prompt: formData.system_prompt,
      tools: formData.tools,
      capabilities: parsedCapabilities,
      rules: formData.rules,
      output_format: formData.output_format || null,
      visibility: formData.visibility as 'private' | 'public',
      is_enabled: formData.is_enabled,
      share_token: shareToken,
    };

    handleEditSave(updateData);
  };

  const isFormValid = () => {
    return (
      formData.agent_name.trim().length > 0 &&
      formData.agent_name.length <= 100 &&
      formData.system_prompt.trim().length >= 10 &&
      formData.tools.length > 0
    );
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">My Agents</h1>
          <p className="text-muted-foreground mt-2">
            Manage your {instances.length} personal agent instance{instances.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={() => navigate('/agents/templates')} className="gap-2">
          <Plus className="h-4 w-4" />
          Create New Agent
        </Button>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4">
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

            {/* Visibility Filter */}
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <Button
                variant={selectedVisibility === null ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedVisibility(null)}
              >
                All Agents
              </Button>
              <Button
                variant={selectedVisibility === 'default' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedVisibility('default')}
              >
                Default
              </Button>
              <Button
                variant={selectedVisibility === 'private' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedVisibility('private')}
              >
                Private
              </Button>
              {ENABLE_MARKETPLACE && (
                <Button
                  variant={selectedVisibility === 'public' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedVisibility('public')}
                >
                  Public
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Create Success Message */}
      {createSuccess && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">{createSuccess}</AlertDescription>
        </Alert>
      )}

      {/* Bulk Create Success Message */}
      {bulkCreateSuccess && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">{bulkCreateSuccess}</AlertDescription>
        </Alert>
      )}

      {/* Delete Success Message */}
      {deleteSuccess && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">{deleteSuccess}</AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
          <Button onClick={loadInstances} variant="outline" size="sm" className="mt-2">
            Retry
          </Button>
        </Alert>
      )}

      {/* Loading State */}
      {(loading || templatesLoading) && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {/* Templates and Instances Grid */}
      {!loading && !templatesLoading && (filteredTemplates.length > 0 || filteredInstances.length > 0) && (
        <div className="space-y-4">
          {/* Show Templates in Default Tab */}
          {filteredTemplates.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Available Agent Templates
                </h2>
                <Button
                  onClick={handleBulkCreate}
                  disabled={bulkCreating || templatesLoading}
                  size="sm"
                  className="gap-2"
                >
                  {bulkCreating && <Loader2 className="h-4 w-4 animate-spin" />}
                  {bulkCreating ? 'Creating All...' : 'Create All'}
                </Button>
              </div>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredTemplates.map(template => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    onViewDetails={handleViewTemplateDetails}
                    onInstantiate={handleInstantiateTemplate}
                    creating={creating}
                    alreadyExists={existingTemplateIds.has(template.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Show Instances */}
          {filteredInstances.length > 0 && (
            <div>
              {filteredTemplates.length > 0 && (
                <h2 className="text-lg font-semibold mb-3 mt-6">Your Agent Instances</h2>
              )}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {filteredInstances.map(instance => (
                  <AgentCard
                    key={instance.id}
                    instance={instance}
                    onViewDetails={handleViewDetails}
                    onEdit={handleEditClick}
                    onDelete={handleDeleteClick}
                    onToggleEnabled={toggleEnabled}
                    formatDate={formatDate}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!loading && !templatesLoading && filteredInstances.length === 0 && filteredTemplates.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg font-semibold mb-2">
              {instances.length === 0 && templates.length === 0 ? 'No agents available' : 'No matching agents'}
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              {instances.length === 0 && templates.length === 0
                ? 'No agent templates or instances found'
                : 'Try adjusting your filters or search terms'}
            </p>
            {(instances.length > 0 || templates.length > 0) && (
              <Button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedVisibility(null);
                }}
              >
                Clear Filters
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Stats Footer */}
      {!loading && !templatesLoading && (instances.length > 0 || templates.length > 0) && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <div>
                Showing {filteredInstances.length + filteredTemplates.length} of {instances.length + (selectedVisibility === 'default' ? templates.length : 0)} agent{(instances.length + templates.length) !== 1 ? 's' : ''}
              </div>
              <div className="flex items-center gap-4">
                {selectedVisibility === 'default' && templates.length > 0 && (
                  <div>
                    Templates: {templates.length}
                  </div>
                )}
                <div>
                  Private: {instances.filter(i => i.visibility === 'private').length}
                </div>
                <div>
                  Public: {instances.filter(i => i.visibility === 'public').length}
                </div>
                <div>
                  Customized: {instances.filter(i => i.is_customized).length}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Details Dialog - Enhanced Large View */}
      {selectedInstance && (() => {
        // Check if agent is callable in dialog
        const isCallableDialog = Boolean(
          selectedInstance.system_prompt &&
          selectedInstance.tools &&
          selectedInstance.tools.length > 0
        );

        // Get visibility label for dialog
        const getVisibilityLabelDialog = (visibility: string) => {
          switch (visibility) {
            case 'default':
              return 'Default';
            case 'private':
              return 'Private';
            case 'public':
              return 'Public';
            default:
              return visibility.charAt(0).toUpperCase() + visibility.slice(1);
          }
        };

        return (
          <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
            <DialogContent className="max-w-7xl max-h-[95vh] overflow-y-auto">
              <DialogHeader className="pb-6 border-b">
                <DialogTitle className="text-3xl font-bold flex items-center gap-3">
                  <Sparkles className="h-7 w-7 text-primary" />
                  {selectedInstance.agent_name}
                </DialogTitle>
                <DialogDescription className="mt-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    <Badge variant="outline" className="text-sm py-1 px-3">
                      {getVisibilityLabelDialog(selectedInstance.visibility)}
                    </Badge>
                    {selectedInstance.is_customized && (
                      <Badge variant="secondary" className="text-sm py-1 px-3">Customized</Badge>
                    )}
                    {isCallableDialog ? (
                      <Badge className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20 text-sm py-1 px-3">
                        <CheckCircle2 className="h-4 w-4 mr-1" />
                        Ready to Call
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-yellow-700 dark:text-yellow-400 border-yellow-500/40 text-sm py-1 px-3">
                        <AlertCircle className="h-4 w-4 mr-1" />
                        Not Ready
                      </Badge>
                    )}
                  </div>
                </DialogDescription>
              </DialogHeader>

            <div className="space-y-8 py-6">
              {/* Stats Cards - Larger and more prominent - Responsive */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="p-6 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 text-center">
                  <Activity className="h-8 w-8 text-primary mx-auto mb-2" />
                  <p className="text-4xl font-bold text-primary">{selectedInstance.usage_count || 0}</p>
                  <p className="text-sm text-muted-foreground mt-1">Total Uses</p>
                </div>
                <div className="p-6 rounded-lg bg-muted/50 border text-center">
                  <Calendar className="h-8 w-8 text-primary mx-auto mb-2" />
                  <p className="text-lg font-bold">{formatDate(selectedInstance.created_at)}</p>
                  <p className="text-sm text-muted-foreground mt-1">Created</p>
                </div>
                <div className="p-6 rounded-lg bg-muted/50 border text-center">
                  <Calendar className="h-8 w-8 text-primary mx-auto mb-2" />
                  <p className="text-lg font-bold">
                    {selectedInstance.last_used_at
                      ? formatDate(selectedInstance.last_used_at)
                      : 'Never'}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">Last Used</p>
                </div>
              </div>

              {/* System Prompt - Full width, larger font, no height limit */}
              {selectedInstance.system_prompt && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-xl flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      System Prompt
                    </h3>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(selectedInstance.system_prompt);
                      }}
                      className="gap-2"
                    >
                      Copy
                    </Button>
                  </div>
                  <div className="bg-muted/50 p-6 rounded-lg border">
                    <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed">
                      {selectedInstance.system_prompt}
                    </pre>
                  </div>
                </div>
              )}

              {/* Tools */}
              {selectedInstance.tools && selectedInstance.tools.length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-bold text-xl flex items-center gap-2">
                    Tools
                    <Badge variant="secondary" className="ml-2">{selectedInstance.tools.length}</Badge>
                  </h3>
                  <div className="bg-muted/30 p-4 rounded-lg border">
                    <div className="flex flex-wrap gap-2">
                      {selectedInstance.tools.map((tool, idx) => (
                        <Badge key={idx} variant="secondary" className="text-sm py-1 px-3">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Capabilities */}
              {selectedInstance.capabilities && Object.keys(selectedInstance.capabilities).length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-bold text-xl flex items-center gap-2">
                    Capabilities
                    <Badge variant="secondary" className="ml-2">
                      {Object.keys(selectedInstance.capabilities).length}
                    </Badge>
                  </h3>
                  <div className="bg-muted/30 p-4 rounded-lg border space-y-3">
                    {Object.entries(selectedInstance.capabilities).map(([key, value]) => (
                      <div key={key} className="flex flex-col gap-1 text-sm border-b pb-2 last:border-b-0">
                        <span className="font-semibold text-primary">{key}</span>
                        <span className="text-muted-foreground pl-4">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rules - Full width */}
              {selectedInstance.rules && Array.isArray(selectedInstance.rules) && selectedInstance.rules.length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-bold text-xl flex items-center gap-2">
                    Rules
                    <Badge variant="secondary" className="ml-2">{selectedInstance.rules.length}</Badge>
                  </h3>
                  <div className="bg-muted/30 p-4 rounded-lg border space-y-3">
                    {selectedInstance.rules.map((rule, idx) => (
                      <div key={idx} className="flex gap-3 text-sm p-3 bg-background rounded border">
                        <span className="text-primary font-bold text-base">{idx + 1}.</span>
                        <span className="flex-1 leading-relaxed">
                          {typeof rule === 'string' ? rule : JSON.stringify(rule)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Separator />

            <DialogFooter className="pt-4">
              <Button variant="outline" onClick={() => setIsDetailsDialogOpen(false)} className="px-8">
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        );
      })()}

      {/* Template Details Dialog */}
      {selectedTemplate && (
        <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-2xl">
                <Sparkles className="h-6 w-6 text-primary" />
                {selectedTemplate.name}
              </DialogTitle>
              <DialogDescription>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <Badge variant="outline">Template</Badge>
                  {selectedTemplate.category && (
                    <Badge variant="secondary">{selectedTemplate.category}</Badge>
                  )}
                  {selectedTemplate.version && (
                    <Badge variant="outline">v{selectedTemplate.version}</Badge>
                  )}
                </div>
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-4">
              {/* Description */}
              {selectedTemplate.description && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">Description</h3>
                  <p className="text-sm text-muted-foreground">{selectedTemplate.description}</p>
                </div>
              )}

              {/* System Prompt Preview */}
              {selectedTemplate.system_prompt && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">System Prompt</h3>
                  <div className="bg-muted p-4 rounded-lg max-h-60 overflow-y-auto">
                    <pre className="text-xs whitespace-pre-wrap font-mono">
                      {selectedTemplate.system_prompt}
                    </pre>
                  </div>
                </div>
              )}

              {/* Tools */}
              {selectedTemplate.tools && selectedTemplate.tools.length > 0 && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">
                    Tools ({selectedTemplate.tools.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedTemplate.tools.map((tool, idx) => (
                      <Badge key={idx} variant="secondary">{tool}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Capabilities */}
              {selectedTemplate.capabilities && Object.keys(selectedTemplate.capabilities).length > 0 && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">
                    Capabilities ({Object.keys(selectedTemplate.capabilities).length})
                  </h3>
                  <div className="bg-muted p-4 rounded-lg space-y-2 max-h-60 overflow-y-auto">
                    {Object.entries(selectedTemplate.capabilities).map(([key, value]) => (
                      <div key={key} className="flex gap-2 text-sm">
                        <span className="font-semibold text-primary min-w-32">{key}:</span>
                        <span className="text-muted-foreground">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rules */}
              {selectedTemplate.rules && Array.isArray(selectedTemplate.rules) && selectedTemplate.rules.length > 0 && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">Rules</h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedTemplate.rules.map((rule, idx) => (
                      <div key={idx} className="flex gap-2 text-sm p-2 bg-muted rounded">
                        <span className="text-primary font-semibold">{idx + 1}.</span>
                        <span>{typeof rule === 'string' ? rule : JSON.stringify(rule)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Separator />

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setIsDetailsDialogOpen(false)}
                disabled={creating}
              >
                Close
              </Button>
              <Button
                onClick={() => handleInstantiateTemplate(selectedTemplate)}
                className="gap-2"
                disabled={creating}
              >
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    Create Instance
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Edit Agent Dialog */}
      {instanceToEdit && (
        <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl">Edit Agent: {instanceToEdit.agent_name}</DialogTitle>
              <DialogDescription>
                Customize your agent's configuration, tools, and behavior.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-4">
              {/* Error Message */}
              {editError && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{editError}</AlertDescription>
                </Alert>
              )}

              {/* Section 1: Basic Information */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold border-b pb-2">Basic Information</h3>

                {/* Agent Name */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Agent Name <span className="text-destructive">*</span>
                  </label>
                  <Input
                    value={formData.agent_name}
                    onChange={(e) => handleInputChange('agent_name', e.target.value)}
                    placeholder="Enter agent name"
                    maxLength={100}
                  />
                  <p className="text-xs text-muted-foreground">
                    {formData.agent_name.length}/100 characters
                  </p>
                </div>

                {/* Visibility */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Visibility</label>
                  <div className="flex gap-4">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="visibility"
                        value="private"
                        checked={formData.visibility === 'private'}
                        onChange={(e) => handleInputChange('visibility', e.target.value)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Private</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        name="visibility"
                        value="public"
                        checked={formData.visibility === 'public'}
                        onChange={(e) => handleInputChange('visibility', e.target.value)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Public</span>
                    </label>
                  </div>
                </div>

                {/* Is Enabled */}
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="is_enabled"
                    checked={formData.is_enabled}
                    onCheckedChange={(checked) => handleInputChange('is_enabled', checked)}
                  />
                  <label htmlFor="is_enabled" className="text-sm font-medium cursor-pointer">
                    Agent Enabled
                  </label>
                </div>
              </div>

              <Separator />

              {/* Section 2: Configuration */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold border-b pb-2">Configuration</h3>

                {/* System Prompt */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    System Prompt <span className="text-destructive">*</span>
                  </label>
                  <textarea
                    value={formData.system_prompt}
                    onChange={(e) => handleInputChange('system_prompt', e.target.value)}
                    placeholder="Enter system prompt (minimum 10 characters)"
                    rows={10}
                    className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background resize-y"
                  />
                  <p className="text-xs text-muted-foreground">
                    {formData.system_prompt.length} characters (minimum 10 required)
                  </p>
                </div>

                {/* Tools */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Tools <span className="text-destructive">*</span>
                  </label>
                  <div className="flex gap-2">
                    <Input
                      value={newTool}
                      onChange={(e) => setNewTool(e.target.value)}
                      placeholder="Add tool name"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddTool();
                        }
                      }}
                    />
                    <Button type="button" onClick={handleAddTool} size="sm">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.tools.map((tool, index) => {
                      // Handle both string and object formats
                      const toolName = typeof tool === 'string' ? tool : (tool as any)?.name || JSON.stringify(tool);
                      return (
                        <Badge key={index} variant="secondary" className="gap-1">
                          {toolName}
                          <button
                            onClick={() => handleRemoveTool(index)}
                            className="ml-1 hover:text-destructive"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      );
                    })}
                  </div>
                  {formData.tools.length === 0 && (
                    <p className="text-xs text-destructive">At least 1 tool is required</p>
                  )}
                </div>

                {/* Capabilities */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Capabilities (JSON)</label>
                  <textarea
                    value={formData.capabilities}
                    onChange={(e) => handleInputChange('capabilities', e.target.value)}
                    placeholder='{"key": "value"}'
                    rows={6}
                    className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background font-mono resize-y"
                  />
                  {capabilitiesError && (
                    <p className="text-xs text-destructive">{capabilitiesError}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Enter capabilities as valid JSON
                  </p>
                </div>
              </div>

              <Separator />

              {/* Section 3: Rules & Output */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold border-b pb-2">Rules & Output</h3>

                {/* Rules */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Rules</label>
                  <div className="flex gap-2">
                    <Input
                      value={newRule}
                      onChange={(e) => setNewRule(e.target.value)}
                      placeholder="Add a rule"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddRule();
                        }
                      }}
                    />
                    <Button type="button" onClick={handleAddRule} size="sm">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="space-y-2 mt-2 max-h-40 overflow-y-auto">
                    {formData.rules.map((rule, index) => {
                      // Handle both string and object formats
                      const ruleText = typeof rule === 'string' ? rule : (rule as any)?.content || (rule as any)?.name || JSON.stringify(rule);
                      return (
                        <div key={index} className="flex gap-2 items-start p-2 bg-muted rounded">
                          <span className="text-primary font-semibold text-sm">{index + 1}.</span>
                          <span className="text-sm flex-1">{ruleText}</span>
                          <button
                            onClick={() => handleRemoveRule(index)}
                            className="text-destructive hover:text-destructive/80"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Output Format */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Output Format</label>
                  <textarea
                    value={formData.output_format}
                    onChange={(e) => handleInputChange('output_format', e.target.value)}
                    placeholder="Enter output format specifications"
                    rows={4}
                    className="w-full px-3 py-2 text-sm rounded-md border border-input bg-background resize-y"
                  />
                </div>
              </div>
            </div>

            <Separator />

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setIsEditDialogOpen(false)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button
                onClick={handleEditFormSave}
                disabled={!isFormValid() || saving}
                className="gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent Instance?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{instanceToDelete?.agent_name}"? This action cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDeleteDialogOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="gap-2"
            >
              {deleting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4" />
                  Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

/**
 * Template Card Component
 * Individual card for each agent template
 */
interface TemplateCardProps {
  template: AgentTemplate;
  onViewDetails: (template: AgentTemplate) => void;
  onInstantiate: (template: AgentTemplate) => void;
  creating: boolean;
  alreadyExists: boolean;
}

const TemplateCard: React.FC<TemplateCardProps> = ({ template, onViewDetails, onInstantiate, creating, alreadyExists }) => {
  const toolsCount = template.tools ? template.tools.length : 0;
  const capabilitiesCount = template.capabilities ? Object.keys(template.capabilities).length : 0;

  return (
    <Card className="group hover:shadow-lg transition-all hover:border-primary/50 bg-gradient-to-br from-primary/5 to-transparent">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              {template.name}
            </CardTitle>
            <CardDescription className="mt-2">
              <span className="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" className="text-xs bg-primary/10">
                  Template
                </Badge>
                {template.category && (
                  <Badge variant="secondary" className="text-xs">
                    {template.category}
                  </Badge>
                )}
                {template.version && (
                  <Badge variant="outline" className="text-xs">
                    v{template.version}
                  </Badge>
                )}
              </span>
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Description */}
        {template.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {template.description}
          </p>
        )}

        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Sparkles className="h-3 w-3" />
            Ready to use
          </div>
          <div className="flex items-center gap-1">
            <span>{toolsCount} tools</span>
            <span>•</span>
            <span>{capabilitiesCount} capabilities</span>
          </div>
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1 gap-2"
            onClick={() => onViewDetails(template)}
            disabled={creating}
          >
            <Eye className="h-4 w-4" />
            View
          </Button>
          {alreadyExists ? (
            <Button
              variant="secondary"
              className="flex-1 gap-2"
              disabled
            >
              <CheckCircle2 className="h-4 w-4" />
              Already Created
            </Button>
          ) : (
            <Button
              className="flex-1 gap-2"
              onClick={() => onInstantiate(template)}
              disabled={creating}
            >
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  Create
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * Agent Card Component
 * Individual card for each agent instance
 */
interface AgentCardProps {
  instance: UserAgentInstance;
  onViewDetails: (instance: UserAgentInstance) => void;
  onEdit: (instance: UserAgentInstance) => void;
  onDelete: (instance: UserAgentInstance) => void;
  onToggleEnabled: (instanceId: string, enabled: boolean) => Promise<boolean>;
  formatDate: (date: string) => string;
}

const AgentCard: React.FC<AgentCardProps> = ({ instance, onViewDetails, onEdit, onDelete, onToggleEnabled, formatDate }) => {
  const [isToggling, setIsToggling] = React.useState(false);
  const toolsCount = instance.tools ? instance.tools.length : 0;
  const capabilitiesCount = instance.capabilities ? Object.keys(instance.capabilities).length : 0;

  // Check if agent is callable (has required configuration for call_agent)
  const isCallable = Boolean(
    instance.system_prompt &&
    instance.tools &&
    instance.tools.length > 0
  );

  // Handle toggle enabled/disabled
  const handleToggleEnabled = async (checked: boolean) => {
    setIsToggling(true);
    await onToggleEnabled(instance.id, checked);
    setIsToggling(false);
  };

  // Get visibility label based on instance visibility
  const getVisibilityLabel = (visibility: string) => {
    switch (visibility) {
      case 'default':
        return 'Default';
      case 'private':
        return 'Private';
      case 'public':
        return 'Public';
      default:
        return visibility.charAt(0).toUpperCase() + visibility.slice(1);
    }
  };

  return (
    <Card className="group hover:shadow-lg transition-all hover:border-primary/50">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {instance.agent_name}
            </CardTitle>
            <div className="flex items-center gap-2 flex-wrap mt-2">
              <Badge variant="outline" className="text-xs">
                {getVisibilityLabel(instance.visibility)}
              </Badge>
              {instance.is_customized && (
                <Badge variant="secondary" className="text-xs">
                  Customized
                </Badge>
              )}
              {isCallable ? (
                <Badge className="text-xs bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Ready to Call
                </Badge>
              ) : (
                <Badge variant="outline" className="text-xs text-yellow-700 dark:text-yellow-400 border-yellow-500/40">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Not Ready
                </Badge>
              )}
              {instance.is_enabled ? (
                <Badge className="text-xs bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20">
                  ✓ Enabled
                </Badge>
              ) : (
                <Badge variant="outline" className="text-xs text-gray-600 dark:text-gray-400">
                  Disabled
                </Badge>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3" />
            {instance.usage_count || 0} {instance.usage_count === 1 ? 'use' : 'uses'}
          </div>
          <div className="flex items-center gap-1">
            <span>{toolsCount} tools</span>
            <span>•</span>
            <span>{capabilitiesCount} capabilities</span>
          </div>
        </div>

        {/* Dates */}
        <div className="text-xs text-muted-foreground space-y-1">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            Created {formatDate(instance.created_at)}
          </div>
          {instance.last_used_at && (
            <div className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              Last used {formatDate(instance.last_used_at)}
            </div>
          )}
        </div>

        <Separator />

        {/* Enable/Disable Toggle */}
        <div className="flex items-center space-x-2 p-2 rounded-md bg-muted/50">
          <Checkbox
            id={`enabled-${instance.id}`}
            checked={instance.is_enabled}
            onCheckedChange={handleToggleEnabled}
            disabled={isToggling}
          />
          <label
            htmlFor={`enabled-${instance.id}`}
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
          >
            {isToggling ? 'Updating...' : (instance.is_enabled ? 'Agent Enabled' : 'Agent Disabled')}
          </label>
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1 gap-2"
            onClick={() => onViewDetails(instance)}
          >
            <Eye className="h-4 w-4" />
            View
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => onEdit(instance)}
            className="hover:text-primary hover:border-primary"
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => onDelete(instance)}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default MyAgentsPage;
