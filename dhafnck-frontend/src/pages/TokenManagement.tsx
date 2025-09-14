import { format } from 'date-fns';
import { AlertCircle, CheckCircle, Clock, Copy, Key, Settings, Shield, Sparkles, XCircle, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AppLayout } from '../components/AppLayout';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import MCPConfigProfile from '../components/ui/MCPConfigProfile';
import { Separator } from '../components/ui/separator';
import { SparklesText } from '../components/ui/SparklesText';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useAuth } from '../hooks/useAuth';
import { tokenService } from '../services/tokenService';

interface APIToken {
  id: string;
  name: string;
  token?: string;
  scopes: string[];
  created_at: string;
  expires_at: string;
  last_used_at?: string;
  usage_count: number;
  rate_limit?: number;
  is_active: boolean;
}

interface ScopeCardProps {
  scope: {
    value: string;
    label: string;
    description: string;
    category: string;
  };
  isSelected: boolean;
  onToggle: (value: string) => void;
}

function ScopeCard({ scope, isSelected, onToggle }: ScopeCardProps) {

  const parsePermission = (value: string) => {
    // Handle special cases first
    if (value === 'openid') return { resource: 'OpenID', verb: 'Connect' };
    if (value === 'profile') return { resource: 'Profile', verb: 'Access' };
    if (value === 'email') return { resource: 'Email', verb: 'Access' };
    if (value === 'offline_access') return { resource: 'Offline', verb: 'Access' };
    if (value === 'mcp-api') return { resource: 'MCP API', verb: 'Access' };
    if (value === 'mcp-roles') return { resource: 'MCP Roles', verb: 'Manage' };
    if (value === 'mcp-profile') return { resource: 'MCP Profile', verb: 'Access' };
    if (value === 'mcp:execute') return { resource: 'MCP', verb: 'Execute' };
    if (value === 'mcp:delegate') return { resource: 'MCP', verb: 'Delegate' };
    
    // Parse standard format: resource:action
    if (value.includes(':')) {
      const [resource, action] = value.split(':');
      const resourceName = resource.charAt(0).toUpperCase() + resource.slice(1);
      const verbName = action.charAt(0).toUpperCase() + action.slice(1);
      return { resource: resourceName, verb: verbName };
    }
    
    // Fallback for unknown formats
    return { resource: scope.label, verb: 'Access' };
  };

  const { resource, verb } = parsePermission(scope.value);

  return (
    <div className="relative group">
      <Card 
        className={`cursor-pointer transition-all duration-200 hover:shadow-lg ${
          isSelected 
            ? 'ring-2 ring-primary shadow-lg bg-gradient-to-br from-primary/10 to-secondary/10' 
            : 'hover:shadow-md bg-gradient-to-br from-surface to-surface-secondary border-border hover:border-primary/20'
        }`}
        onClick={() => onToggle(scope.value)}
      >
        <CardContent className="p-3">
          <div className="flex items-center space-x-2">
            <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all duration-200 ${
              isSelected 
                ? 'bg-primary border-primary text-primary-foreground' 
                : 'border-muted-foreground/30 hover:border-primary/50'
            }`}>
              {isSelected && (
                <svg className="w-2.5 h-2.5 fill-current" viewBox="0 0 12 12">
                  <path d="M10.28 2.28L3.989 8.575 1.695 6.28A1 1 0 00.281 7.695l3 3a1 1 0 001.414 0l7-7A1 1 0 0010.28 2.28z" />
                </svg>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-1">
                <span className="font-medium text-xs text-foreground truncate">{resource}</span>
                <span className="text-[10px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded-full">
                  {verb}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Tooltip on hover */}
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-10 max-w-xs whitespace-normal">
        <div className="text-center">
          <div className="text-gray-300">{scope.description}</div>
        </div>
        {/* Arrow pointing down */}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  );
}

const AVAILABLE_SCOPES = [
  // OpenID Connect Core Scopes
  { value: 'openid', label: 'OpenID', description: 'OpenID Connect authentication', category: 'Core' },
  { value: 'profile', label: 'Profile', description: 'User profile information', category: 'Core' },
  { value: 'email', label: 'Email', description: 'Email address access', category: 'Core' },
  { value: 'offline_access', label: 'Offline Access', description: 'Refresh token for offline access', category: 'Core' },
  
  // MCP API Scopes
  { value: 'mcp-api', label: 'MCP API', description: 'Full MCP API access', category: 'API' },
  { value: 'mcp-roles', label: 'MCP Roles', description: 'Role-based access control', category: 'API' },
  { value: 'mcp-profile', label: 'MCP Profile', description: 'MCP user profile data', category: 'API' },
  
  // Projects CRUD Scopes
  { value: 'projects:create', label: 'Create Projects', description: 'Create new projects', category: 'Projects' },
  { value: 'projects:read', label: 'Read Projects', description: 'View projects and details', category: 'Projects' },
  { value: 'projects:update', label: 'Update Projects', description: 'Modify existing projects', category: 'Projects' },
  { value: 'projects:delete', label: 'Delete Projects', description: 'Delete projects', category: 'Projects' },
  
  // Tasks CRUD Scopes
  { value: 'tasks:create', label: 'Create Tasks', description: 'Create new tasks', category: 'Tasks' },
  { value: 'tasks:read', label: 'Read Tasks', description: 'View tasks and details', category: 'Tasks' },
  { value: 'tasks:update', label: 'Update Tasks', description: 'Modify existing tasks', category: 'Tasks' },
  { value: 'tasks:delete', label: 'Delete Tasks', description: 'Delete tasks', category: 'Tasks' },
  
  // Subtasks CRUD Scopes
  { value: 'subtasks:create', label: 'Create Subtasks', description: 'Create new subtasks', category: 'Subtasks' },
  { value: 'subtasks:read', label: 'Read Subtasks', description: 'View subtasks and details', category: 'Subtasks' },
  { value: 'subtasks:update', label: 'Update Subtasks', description: 'Modify existing subtasks', category: 'Subtasks' },
  { value: 'subtasks:delete', label: 'Delete Subtasks', description: 'Delete subtasks', category: 'Subtasks' },
  
  // Contexts CRUD Scopes
  { value: 'contexts:create', label: 'Create Contexts', description: 'Create new contexts', category: 'Contexts' },
  { value: 'contexts:read', label: 'Read Contexts', description: 'View contexts and data', category: 'Contexts' },
  { value: 'contexts:update', label: 'Update Contexts', description: 'Modify context data', category: 'Contexts' },
  { value: 'contexts:delete', label: 'Delete Contexts', description: 'Delete contexts', category: 'Contexts' },
  
  // Agents CRUD Scopes
  { value: 'agents:create', label: 'Register Agents', description: 'Register new agents', category: 'Agents' },
  { value: 'agents:read', label: 'Read Agents', description: 'View agent configurations', category: 'Agents' },
  { value: 'agents:update', label: 'Update Agents', description: 'Modify agent settings', category: 'Agents' },
  { value: 'agents:delete', label: 'Unregister Agents', description: 'Remove agents', category: 'Agents' },
  
  // Branches CRUD Scopes
  { value: 'branches:create', label: 'Create Branches', description: 'Create new git branches', category: 'Branches' },
  { value: 'branches:read', label: 'Read Branches', description: 'View branches and details', category: 'Branches' },
  { value: 'branches:update', label: 'Update Branches', description: 'Modify branch settings', category: 'Branches' },
  { value: 'branches:delete', label: 'Delete Branches', description: 'Delete branches', category: 'Branches' },
  
  // MCP Execute Scopes
  { value: 'mcp:execute', label: 'Execute MCP', description: 'Run MCP commands and tools', category: 'Execute' },
  { value: 'mcp:delegate', label: 'Delegate MCP', description: 'Delegate MCP operations', category: 'Execute' }
];

export function TokenManagement() {
  useAuth(); // Ensure user is authenticated
  const [activeTab, setActiveTab] = useState('generate');
  const [tokens, setTokens] = useState<APIToken[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Token generation form state
  const [tokenName, setTokenName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [expiryDays, setExpiryDays] = useState(30);
  const [rateLimit, setRateLimit] = useState(1000);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [showTokenDialog, setShowTokenDialog] = useState(false);
  
  // Delete dialog state - using token ID as key for multiple dialogs
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<{[key: string]: boolean}>({});
  
  // Copy state for buttons
  const [copiedButton, setCopiedButton] = useState<string | null>(null);

  useEffect(() => {
    // Only fetch tokens if we're on the Active Tokens tab
    if (activeTab === 'tokens') {
      fetchTokens();
    }
  }, [activeTab]);

  const fetchTokens = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Starting token fetch...');
      const response = await tokenService.listTokens();
      console.log('Fetched tokens response:', response);
      
      if (response && response.data) {
        setTokens(response.data);
        console.log('Set tokens state with:', response.data);
      } else {
        setTokens([]);
        console.log('No data in response, setting empty array');
      }
    } catch (err) {
      console.error('Error fetching tokens:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch tokens';
      setError(errorMessage);
      setTokens([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateToken = async () => {
    if (!tokenName.trim()) {
      setError('Token name is required');
      return;
    }
    if (selectedScopes.length === 0) {
      setError('At least one scope must be selected');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await tokenService.generateToken({
        name: tokenName,
        scopes: selectedScopes,
        expires_in_days: expiryDays,
        rate_limit: rateLimit
      });
      
      setGeneratedToken(response.data.token || null);
      setShowTokenDialog(true);
      setSuccess('Token generated successfully');
      
      // Reset form
      setTokenName('');
      setSelectedScopes([]);
      setExpiryDays(30);
      setRateLimit(1000);
      
      // Refresh token list
      await fetchTokens();
    } catch (err) {
      console.error('Error generating token:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate token');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeToken = async (tokenId: string) => {
    try {
      setLoading(true);
      await tokenService.revokeToken(tokenId);
      setSuccess('Token revoked successfully');
      await fetchTokens();
    } catch (err) {
      setError('Failed to revoke token');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, buttonId?: string) => {
    navigator.clipboard.writeText(text);
    if (buttonId) {
      setCopiedButton(buttonId);
      setTimeout(() => setCopiedButton(null), 2000);
    }
    setSuccess('Copied to clipboard');
    setTimeout(() => setSuccess(null), 2000);
  };

  const handleScopeToggle = (scopeValue: string) => {
    setSelectedScopes(prev => 
      prev.includes(scopeValue) 
        ? prev.filter(s => s !== scopeValue)
        : [...prev, scopeValue]
    );
  };

  const openDeleteDialog = (tokenId: string) => {
    setDeleteDialogOpen(prev => ({ ...prev, [tokenId]: true }));
  };

  const closeDeleteDialog = (tokenId: string) => {
    setDeleteDialogOpen(prev => ({ ...prev, [tokenId]: false }));
  };

  return (
    <AppLayout>
      <div className="container mx-auto p-6 max-w-7xl">
        {/* Header Section */}
        <div className="mb-8">
          <SparklesText 
            as="h1" 
            className="text-4xl font-bold text-foreground mb-4"
            sparkleCount={20}
            sparkleSize={14}
          >
            API Token Management
          </SparklesText>
          <p className="text-muted-foreground text-lg">
            Generate and manage secure API tokens for MCP authentication and integration
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <Alert className="mb-6 border-l-4 border-red-500 bg-red-50 dark:bg-red-950">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="mb-6 border-l-4 border-green-500 bg-green-50 dark:bg-green-950">
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        {/* Modern Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm rounded-lg h-12">
            <TabsTrigger 
              value="generate" 
              className="flex items-center justify-center space-x-2 font-medium h-full data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-indigo-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-all rounded-md"
            >
              <Key size={18} />
              <span>Generate Token</span>
            </TabsTrigger>
            <TabsTrigger 
              value="tokens" 
              className="flex items-center justify-center space-x-2 font-medium h-full data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-indigo-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-all rounded-md"
            >
              <Shield size={18} />
              <span>Active Tokens</span>
            </TabsTrigger>
            <TabsTrigger 
              value="settings" 
              className="flex items-center justify-center space-x-2 font-medium h-full data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-indigo-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-all rounded-md"
            >
              <Settings size={18} />
              <span>Settings</span>
            </TabsTrigger>
          </TabsList>

          {/* Generate Token Tab */}
          <TabsContent value="generate" className="bg-white dark:bg-slate-900 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6">
            <Card className="bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  <span>Generate New API Token</span>
                </CardTitle>
                <CardDescription>
                  Create a secure API token with custom permissions and settings
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Token Name */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Token Name</label>
                  <Input
                    value={tokenName}
                    onChange={(e) => setTokenName(e.target.value)}
                    placeholder="e.g., Production API, CI/CD Pipeline, Development Access"
                    className="bg-background/50"
                  />
                  <p className="text-xs text-muted-foreground">A descriptive name to identify this token</p>
                </div>

                {/* Scope Selection with Improved Grid */}
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Select Permissions</h3>
                    <Badge variant="outline" className="text-sm">
                      {selectedScopes.length} selected
                    </Badge>
                  </div>
                  
                  {/* Quick Actions */}
                  <div className="flex flex-wrap gap-2 p-4 bg-slate-100 dark:bg-slate-700 rounded-lg">
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => setSelectedScopes(AVAILABLE_SCOPES.map(s => s.value))}
                      className="bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white"
                    >
                      <Shield className="h-4 w-4 mr-1" />
                      Full Access
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const readScopes = AVAILABLE_SCOPES
                          .filter(s => s.value.includes(':read') || s.category === 'Core' || s.category === 'API')
                          .map(s => s.value);
                        setSelectedScopes(readScopes);
                      }}
                    >
                      Read Only
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const essentialScopes = [
                          'openid', 'profile', 'email', 'mcp-api', 'mcp-roles',
                          'projects:read', 'tasks:read', 'tasks:create', 'tasks:update',
                          'contexts:read', 'contexts:update'
                        ];
                        setSelectedScopes(essentialScopes);
                      }}
                    >
                      Essential
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const executeScopes = [
                          'openid', 'profile', 'email', 'mcp-api', 'mcp-roles', 'mcp-profile',
                          'mcp:execute', 'mcp:delegate'
                        ];
                        setSelectedScopes(executeScopes);
                      }}
                    >
                      <Zap className="h-4 w-4 mr-1" />
                      Execute Only
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedScopes([])}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      Clear All
                    </Button>
                  </div>

                  {/* Improved Grid Layout for Scopes */}
                  {['Core', 'API', 'Projects', 'Tasks', 'Subtasks', 'Contexts', 'Agents', 'Branches', 'Execute'].map((category) => {
                    const categoryScopes = AVAILABLE_SCOPES.filter(s => s.category === category);
                    if (categoryScopes.length === 0) return null;
                    
                    return (
                      <div key={category} className="space-y-3">
                        <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
                          {category} Permissions
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                          {categoryScopes.map((scope) => (
                            <ScopeCard
                              key={scope.value}
                              scope={scope}
                              isSelected={selectedScopes.includes(scope.value)}
                              onToggle={handleScopeToggle}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Settings Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center space-x-2">
                      <Clock className="h-4 w-4" />
                      <span>Expiry (days)</span>
                    </label>
                    <Input
                      type="number"
                      value={expiryDays}
                      onChange={(e) => setExpiryDays(parseInt(e.target.value) || 30)}
                      min="1"
                      max="365"
                      className="bg-background/50"
                    />
                    <p className="text-xs text-muted-foreground">Token expires after this many days</p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center space-x-2">
                      <Zap className="h-4 w-4" />
                      <span>Rate Limit (requests/hour)</span>
                    </label>
                    <Input
                      type="number"
                      value={rateLimit}
                      onChange={(e) => setRateLimit(parseInt(e.target.value) || 1000)}
                      min="1"
                      max="10000"
                      className="bg-background/50"
                    />
                    <p className="text-xs text-muted-foreground">Maximum requests per hour</p>
                  </div>
                </div>

                {/* Generate Button */}
                <div className="flex justify-between items-center p-4 bg-gradient-to-r from-primary/10 to-secondary/10 rounded-lg border">
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {selectedScopes.length} permission{selectedScopes.length !== 1 ? 's' : ''} selected
                    </p>
                    {tokenName && (
                      <p className="text-xs text-muted-foreground">
                        Token name: "{tokenName}"
                      </p>
                    )}
                  </div>
                  <Button
                    onClick={handleGenerateToken}
                    disabled={loading || !tokenName || selectedScopes.length === 0}
                    className="bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 text-white font-semibold px-8"
                    size="lg"
                  >
                    {loading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Generating...</span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <Key className="h-4 w-4" />
                        <span>Generate API Token</span>
                      </div>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Active Tokens Tab */}
          <TabsContent value="tokens" className="bg-white dark:bg-slate-900 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">Active API Tokens</h2>
                <p className="text-muted-foreground">
                  {tokens.length} active token{tokens.length !== 1 ? 's' : ''}
                </p>
              </div>
              <Button
                variant="outline"
                onClick={fetchTokens}
                disabled={loading}
                className="bg-background/50 hover:bg-background"
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                ) : (
                  <Shield className="h-4 w-4 mr-2" />
                )}
                Refresh
              </Button>
            </div>
            
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : tokens.length === 0 ? (
              <Card className="p-8 text-center bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700">
                <div className="mb-6">
                  <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900 dark:to-indigo-900 rounded-full flex items-center justify-center mb-4">
                    <Key className="h-8 w-8 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">No API Tokens Yet</h3>
                  <p className="text-muted-foreground mb-4">
                    Generate your first token to start using the MCP API
                  </p>
                  <Button
                    onClick={() => setActiveTab('generate')}
                    className="bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 text-white"
                  >
                    <Key className="h-4 w-4 mr-2" />
                    Generate First Token
                  </Button>
                </div>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {tokens.map((token) => {
                  const isExpiringSoon = new Date(token.expires_at) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
                  const isExpired = new Date(token.expires_at) < new Date();
                  
                  return (
                    <Card 
                      key={token.id} 
                      className={`relative overflow-hidden bg-white dark:bg-slate-800 hover:shadow-lg transition-all duration-300 border ${
                        isExpired ? 'border-red-300 bg-red-50 dark:bg-red-950' : isExpiringSoon ? 'border-orange-300 bg-orange-50 dark:bg-orange-950' : 'border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      <CardHeader className="pb-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <CardTitle className="text-lg mb-2 flex items-center space-x-2">
                              <span className="truncate">{token.name}</span>
                            </CardTitle>
                            <div className="flex items-center space-x-2">
                              <Badge 
                                variant={token.is_active && !isExpired ? "default" : "secondary"}
                                className={`${
                                  token.is_active && !isExpired 
                                    ? "bg-green-500 hover:bg-green-600 text-white" 
                                    : "bg-gray-500 text-white"
                                }`}
                              >
                                {isExpired ? 'Expired' : token.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                              {isExpiringSoon && !isExpired && (
                                <Badge variant="outline" className="border-orange-500 text-orange-600">
                                  Expiring Soon
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="space-y-4">
                        {/* Dates */}
                        <div className="grid grid-cols-1 gap-2 text-sm">
                          <div className="flex items-center space-x-2 text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span className="text-xs">Created: {format(new Date(token.created_at), 'MMM d, yyyy')}</span>
                          </div>
                          <div className="flex items-center space-x-2 text-muted-foreground">
                            <AlertCircle className="h-3 w-3" />
                            <span className="text-xs">Expires: {format(new Date(token.expires_at), 'MMM d, yyyy')}</span>
                          </div>
                          {token.last_used_at && (
                            <div className="flex items-center space-x-2 text-muted-foreground">
                              <Zap className="h-3 w-3" />
                              <span className="text-xs">Last used: {format(new Date(token.last_used_at), 'MMM d, h:mm a')}</span>
                            </div>
                          )}
                        </div>
                        
                        <Separator />
                        
                        {/* Usage Stats */}
                        <div className="grid grid-cols-2 gap-4 text-center">
                          <div className="bg-background/50 rounded-lg p-3">
                            <p className="text-2xl font-bold text-primary">{token.usage_count}</p>
                            <p className="text-xs text-muted-foreground">Requests</p>
                          </div>
                          {token.rate_limit && (
                            <div className="bg-background/50 rounded-lg p-3">
                              <p className="text-2xl font-bold text-secondary">{token.rate_limit}</p>
                              <p className="text-xs text-muted-foreground">Per Hour</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Revoke Button */}
                        <div className="pt-4">
                          <Button
                            variant="destructive"
                            size="sm"
                            className="w-full"
                            onClick={() => openDeleteDialog(token.id)}
                          >
                            <XCircle className="h-4 w-4 mr-2" />
                            Revoke Token
                          </Button>
                          
                          {/* Revoke Dialog - Separate from button */}
                          <Dialog 
                            open={deleteDialogOpen[token.id] || false}
                            onOpenChange={(open) => !open && closeDeleteDialog(token.id)}
                          >
                            <DialogContent>
                              <DialogHeader>
                                <DialogTitle>Revoke API Token</DialogTitle>
                                <DialogDescription>
                                  Are you sure you want to revoke the token <strong>"{token.name}"</strong>? This action cannot be undone and any applications using this token will lose access immediately.
                                </DialogDescription>
                              </DialogHeader>
                              <DialogFooter>
                                <Button variant="outline" onClick={() => closeDeleteDialog(token.id)}>
                                  Cancel
                                </Button>
                                <Button
                                  variant="destructive"
                                  onClick={() => {
                                    handleRevokeToken(token.id);
                                    closeDeleteDialog(token.id);
                                  }}
                                >
                                  Revoke Token
                                </Button>
                              </DialogFooter>
                            </DialogContent>
                          </Dialog>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="bg-white dark:bg-slate-900 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6">
            <Card className="bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="h-5 w-5 text-primary" />
                  <span>Token Settings</span>
                </CardTitle>
                <CardDescription>
                  Configure default settings for API token generation and management
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Alert className="border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Token settings configuration will be available in a future update.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Generated Token Dialog */}
        <Dialog open={showTokenDialog} onOpenChange={setShowTokenDialog}>
          <DialogContent className="max-w-5xl max-h-[95vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span>MCP Configuration Generated</span>
              </DialogTitle>
              <DialogDescription>
                Your token has been generated and is ready for Claude Code MCP integration. Save this configuration securely.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              <Alert className="border-l-4 border-orange-500 bg-orange-50 dark:bg-orange-950">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Important:</strong> This token will only be shown once. Copy the configuration now and store it securely.
                </AlertDescription>
              </Alert>
              
              {/* MCP Configuration Display */}
              <MCPConfigProfile 
                configData={{
                  serverName: "DhafnckMCP",
                  protocol: "HTTP",
                  version: "2.1.0",
                  host: (import.meta as any).env?.VITE_API_URL?.replace(/^https?:\/\//, '').replace(/:\d+$/, '') || 'localhost',
                  port: parseInt((import.meta as any).env?.VITE_API_URL?.match(/:(\d+)$/)?.[1] || '8000'),
                  authentication: "JWT Bearer",
                  capabilities: selectedScopes,
                  token: generatedToken || undefined,
                  expiresAt: new Date(Date.now() + expiryDays * 24 * 60 * 60 * 1000).toISOString()
                }}
                showToken={true}
              />
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold">Quick Actions</h4>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const config = {
                          type: "http",
                          url: `${(import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'}/mcp`,
                          headers: {
                            Accept: "application/json, text/event-stream",
                            Authorization: `Bearer ${generatedToken}`
                          }
                        };
                        const configString = `"dhafnck_mcp_http": ${JSON.stringify(config, null, 2)}`;
                        copyToClipboard(configString, 'mcp-config');
                      }}
                      className={copiedButton === 'mcp-config' ? 'bg-green-50 border-green-500 text-green-700' : ''}
                    >
                      {copiedButton === 'mcp-config' ? (
                        <>
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3 mr-1" />
                          Copy MCP Config
                        </>
                      )}
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => generatedToken && copyToClipboard(generatedToken, 'token-only')}
                      className={copiedButton === 'token-only' ? 'bg-green-50 border-green-500 text-green-700' : ''}
                    >
                      {copiedButton === 'token-only' ? (
                        <>
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3 mr-1" />
                          Copy Token Only
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <Card className="p-4">
                    <h5 className="font-medium mb-2 flex items-center">
                      <Settings className="h-4 w-4 mr-2" />
                      Setup Instructions
                    </h5>
                    <div className="space-y-2 text-xs text-muted-foreground">
                      <p>1. Copy the MCP configuration above</p>
                      <p>2. Add it to your Claude Code settings</p>
                      <p>3. Restart Claude Code to activate</p>
                      <p>4. Test connection with the health endpoint</p>
                    </div>
                  </Card>
                  
                  <Card className="p-4">
                    <h5 className="font-medium mb-2 flex items-center">
                      <Shield className="h-4 w-4 mr-2" />
                      Security Notes
                    </h5>
                    <div className="space-y-2 text-xs text-muted-foreground">
                      <p>• Token expires in {expiryDays} days</p>
                      <p>• Rate limit: {rateLimit} requests/hour</p>
                      <p>• Scopes: {selectedScopes.join(', ')}</p>
                      <p>• Store token securely (password manager)</p>
                    </div>
                  </Card>
                </div>
              </div>
            </div>
            
            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setShowTokenDialog(false)}>
                Close
              </Button>
              <Button
                onClick={() => {
                  const config = {
                    type: "http", 
                    url: `${(import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'}/mcp`,
                    headers: {
                      Accept: "application/json, text/event-stream",
                      Authorization: `Bearer ${generatedToken}`
                    }
                  };
                  const configString = `"dhafnck_mcp_http": ${JSON.stringify(config, null, 2)}`;
                  copyToClipboard(configString, 'complete-config');
                }}
                className={copiedButton === 'complete-config' 
                  ? "bg-green-600 hover:bg-green-700 text-white"
                  : "bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white"
                }
              >
                {copiedButton === 'complete-config' ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Copied Successfully!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Complete Config
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}