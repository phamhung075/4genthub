import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
  TextField,
  Button,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  CircularProgress,
  Stack,
  Card,
  CardContent,
  FormControlLabel,
  Checkbox,
  Grid
} from '@mui/material';
import { Delete, Copy, Key, Shield, Settings } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { tokenService } from '../services/tokenService';
import { AppLayout } from '../components/AppLayout';
import { format } from 'date-fns';

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

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`token-tabpanel-${index}`}
      aria-labelledby={`token-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
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
  const [tabValue, setTabValue] = useState(0);
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
  
  // Delete confirmation dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [tokenToDelete, setTokenToDelete] = useState<string | null>(null);

  useEffect(() => {
    // Only fetch tokens if we're on the Active Tokens tab
    if (tabValue === 1) {
      fetchTokens();
    }
  }, [tabValue]);

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
      setDeleteDialogOpen(false);
      setTokenToDelete(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard');
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <AppLayout>
      <Container maxWidth="lg">
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            API Token Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Generate and manage API tokens for MCP authentication
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <Paper sx={{ width: '100%' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="token management tabs">
            <Tab label="Generate Token" icon={<Key size={20} />} iconPosition="start" />
            <Tab label="Active Tokens" icon={<Shield size={20} />} iconPosition="start" />
            <Tab label="Settings" icon={<Settings size={20} />} iconPosition="start" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Generate New API Token
                </Typography>
                
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Token Name"
                      value={tokenName}
                      onChange={(e) => setTokenName(e.target.value)}
                      placeholder="e.g., Production API, CI/CD Pipeline"
                      helperText="A descriptive name to identify this token"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Typography variant="subtitle2" gutterBottom>
                      Select Scopes
                    </Typography>
                    {/* Group scopes by category */}
                    {['Core', 'API', 'Projects', 'Tasks', 'Subtasks', 'Contexts', 'Agents', 'Branches', 'Execute'].map((category) => {
                      const categoryScopes = AVAILABLE_SCOPES.filter(s => s.category === category);
                      if (categoryScopes.length === 0) return null;
                      
                      return (
                        <Box key={category} sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                            {category} Scopes
                          </Typography>
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {categoryScopes.map((scope) => (
                              <FormControlLabel
                                key={scope.value}
                                control={
                                  <Checkbox
                                    checked={selectedScopes.includes(scope.value)}
                                    onChange={(e) => {
                                      if (e.target.checked) {
                                        setSelectedScopes([...selectedScopes, scope.value]);
                                      } else {
                                        setSelectedScopes(selectedScopes.filter(s => s !== scope.value));
                                      }
                                    }}
                                    size="small"
                                  />
                                }
                                label={
                                  <Tooltip title={scope.description}>
                                    <Chip 
                                      label={scope.label} 
                                      size="small"
                                      color={
                                        category === 'Core' ? 'secondary' : 
                                        category === 'API' ? 'primary' : 
                                        category === 'Execute' ? 'warning' : 
                                        'default'
                                      }
                                      variant={selectedScopes.includes(scope.value) ? 'filled' : 'outlined'}
                                    />
                                  </Tooltip>
                                }
                              />
                            ))}
                          </Box>
                        </Box>
                      );
                    })}
                    
                    {/* Quick Actions */}
                    <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        color="success"
                        onClick={() => {
                          // Select all scopes
                          const allScopes = AVAILABLE_SCOPES.map(s => s.value);
                          setSelectedScopes(allScopes);
                        }}
                      >
                        Select All
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        color="primary"
                        onClick={() => {
                          // Select MCP tools scopes
                          const mcpToolsScopes = [
                            'openid', 'profile', 'email', 'offline_access',
                            'mcp-api', 'mcp-roles', 'mcp-profile',
                            'mcp:execute', 'mcp:delegate',
                            // Include all CRUD permissions for MCP tools
                            'projects:create', 'projects:read', 'projects:update', 'projects:delete',
                            'tasks:create', 'tasks:read', 'tasks:update', 'tasks:delete',
                            'subtasks:create', 'subtasks:read', 'subtasks:update', 'subtasks:delete',
                            'contexts:create', 'contexts:read', 'contexts:update', 'contexts:delete',
                            'agents:create', 'agents:read', 'agents:update', 'agents:delete',
                            'branches:create', 'branches:read', 'branches:update', 'branches:delete'
                          ];
                          setSelectedScopes(mcpToolsScopes);
                        }}
                      >
                        MCP Tools (Full Access)
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => {
                          // Select all read scopes
                          const readScopes = AVAILABLE_SCOPES
                            .filter(s => s.value.includes(':read'))
                            .map(s => s.value);
                          const coreScopes = ['openid', 'profile', 'email', 'mcp-api', 'mcp-roles'];
                          setSelectedScopes([...new Set([...coreScopes, ...readScopes])]);
                        }}
                      >
                        Read Only
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => {
                          // Select full CRUD for all resources
                          const fullCrudScopes = AVAILABLE_SCOPES
                            .filter(s => ['Projects', 'Tasks', 'Subtasks', 'Contexts', 'Agents', 'Branches'].includes(s.category))
                            .map(s => s.value);
                          const coreScopes = ['openid', 'profile', 'email', 'mcp-api', 'mcp-roles', 'mcp-profile'];
                          setSelectedScopes([...new Set([...coreScopes, ...fullCrudScopes])]);
                        }}
                      >
                        Full CRUD
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => {
                          // Select essential scopes
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
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => setSelectedScopes([])}
                      >
                        Clear All
                      </Button>
                    </Box>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Expiry (days)"
                      value={expiryDays}
                      onChange={(e) => setExpiryDays(parseInt(e.target.value))}
                      helperText="Token will expire after this many days"
                      InputProps={{ inputProps: { min: 1, max: 365 } }}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Rate Limit (requests/hour)"
                      value={rateLimit}
                      onChange={(e) => setRateLimit(parseInt(e.target.value))}
                      helperText="Maximum requests per hour"
                      InputProps={{ inputProps: { min: 1, max: 10000 } }}
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={handleGenerateToken}
                      disabled={loading || !tokenName || selectedScopes.length === 0}
                      startIcon={loading ? <CircularProgress size={20} /> : <Key size={20} />}
                    >
                      Generate Token
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">Active API Tokens</Typography>
              <Button
                size="small"
                onClick={fetchTokens}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={16} /> : <Shield size={16} />}
              >
                Refresh
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Scopes</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Expires</TableCell>
                    <TableCell>Usage</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <CircularProgress />
                      </TableCell>
                    </TableRow>
                  ) : tokens.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography variant="body2" color="text.secondary">
                          No API tokens found. Generate your first token to get started.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    tokens.map((token) => (
                      <TableRow key={token.id}>
                        <TableCell>{token.name}</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5} flexWrap="wrap">
                            {token.scopes.map((scope) => (
                              <Chip key={scope} label={scope} size="small" />
                            ))}
                          </Stack>
                        </TableCell>
                        <TableCell>
                          {format(new Date(token.created_at), 'MMM d, yyyy')}
                        </TableCell>
                        <TableCell>
                          {format(new Date(token.expires_at), 'MMM d, yyyy')}
                        </TableCell>
                        <TableCell>
                          {token.usage_count} requests
                          {token.last_used_at && (
                            <Typography variant="caption" display="block">
                              Last: {format(new Date(token.last_used_at), 'MMM d')}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={token.is_active ? 'Active' : 'Inactive'}
                            color={token.is_active ? 'success' : 'default'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <IconButton
                            onClick={() => {
                              setTokenToDelete(token.id);
                              setDeleteDialogOpen(true);
                            }}
                            color="error"
                            size="small"
                          >
                            <Delete size={18} />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Token Settings
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Configure default settings for API token generation and management.
                </Typography>
                
                <Alert severity="info" sx={{ mt: 2 }}>
                  Token settings configuration will be available in a future update.
                </Alert>
              </CardContent>
            </Card>
          </TabPanel>
        </Paper>

        {/* Generated Token Dialog */}
        <Dialog 
          open={showTokenDialog} 
          onClose={() => setShowTokenDialog(false)} 
          maxWidth="md" 
          fullWidth
          PaperProps={{
            sx: { maxHeight: '90vh' }
          }}
        >
          <DialogTitle>Token Generated Successfully</DialogTitle>
          <DialogContent dividers sx={{ pb: 3 }}>
            <Alert severity="warning" sx={{ mb: 2 }}>
              Make sure to copy this token now. You won't be able to see it again!
            </Alert>
            <TextField
              fullWidth
              multiline
              rows={3}
              value={generatedToken || ''}
              InputProps={{
                readOnly: true,
                sx: { fontFamily: 'monospace', fontSize: '0.85rem' }
              }}
              sx={{ mb: 2 }}
            />
            
            <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
              How to Use This Token
            </Typography>
            
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              For Claude Code MCP Configuration:
            </Typography>
            <Paper sx={{ p: 2, bgcolor: 'grey.100', mb: 2 }}>
              <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
{`"dhafnck_mcp_http": {
    "type": "http",
    "url": "${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/mcp",
    "headers": {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer ${generatedToken || 'YOUR_TOKEN_HERE'}"
    }
}`}
              </Typography>
            </Paper>
            <Button
              size="small"
              startIcon={<Copy size={16} />}
              onClick={() => {
                const config = {
                  dhafnck_mcp_http: {
                    type: "http",
                    url: `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/mcp`,
                    headers: {
                      Accept: "application/json, text/event-stream",
                      Authorization: `Bearer ${generatedToken}`
                    }
                  }
                };
                copyToClipboard(JSON.stringify(config, null, 4));
                setSuccess('MCP configuration copied to clipboard');
              }}
            >
              Copy MCP Configuration
            </Button>
            
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              For API Requests:
            </Typography>
            <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                Authorization: Bearer {generatedToken ? `${generatedToken.substring(0, 20)}...` : 'YOUR_TOKEN_HERE'}
              </Typography>
            </Paper>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowTokenDialog(false)}>Close</Button>
            <Button
              variant="contained"
              startIcon={<Copy size={18} />}
              onClick={() => generatedToken && copyToClipboard(generatedToken)}
            >
              Copy Token Only
            </Button>
          </DialogActions>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Revoke API Token</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to revoke this token? This action cannot be undone and any applications using this token will lose access.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button
              color="error"
              variant="contained"
              onClick={() => tokenToDelete && handleRevokeToken(tokenToDelete)}
            >
              Revoke Token
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </AppLayout>
  );
}