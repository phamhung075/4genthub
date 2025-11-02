/**
 * Shared Agent Preview Modal
 *
 * Preview publicly shared agents before importing them.
 * Shows read-only configuration with creator attribution.
 *
 * @module components/agents/SharedAgentPreview
 * @version 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  Download,
  User,
  AlertCircle,
  CheckCircle2,
  Loader2,
  X,
  FileText,
  ListChecks,
  Settings2,
  FileOutput,
  Wrench,
  Sparkles,
} from 'lucide-react';
import { useAgentMarketplace, useAgentSharing } from '../../hooks/useAgentManagement';
import type { SharedAgentPreviewResponse } from '../../types/agentTypes';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription } from '../ui/alert';
import { Separator } from '../ui/separator';
import logger from '../../utils/logger';

interface SharedAgentPreviewProps {
  shareToken: string | null;
  isOpen: boolean;
  onClose: () => void;
  onImportSuccess?: (agentName: string) => void;
}

/**
 * Shared Agent Preview Modal
 * Displays read-only preview of shared agent configuration
 */
export const SharedAgentPreview: React.FC<SharedAgentPreviewProps> = ({
  shareToken,
  isOpen,
  onClose,
  onImportSuccess,
}) => {
  const { previewAgent } = useAgentMarketplace();
  const { importAgent, loading: importing, error: importError } = useAgentSharing();

  // Local state
  const [preview, setPreview] = useState<SharedAgentPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('instructions');
  const [importSuccess, setImportSuccess] = useState(false);

  // Load preview when dialog opens with share token
  useEffect(() => {
    const loadPreview = async () => {
      if (!isOpen || !shareToken) {
        setPreview(null);
        setError(null);
        setImportSuccess(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const data = await previewAgent(shareToken);
        if (data) {
          setPreview(data);
          logger.info(`Loaded preview for agent: ${data.agent_name}`);
        } else {
          setError('Failed to load agent preview');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error loading preview';
        setError(errorMessage);
        logger.error('Error loading agent preview:', err);
      } finally {
        setLoading(false);
      }
    };

    loadPreview();
  }, [isOpen, shareToken, previewAgent]);

  // Handle import
  const handleImport = async () => {
    if (!shareToken || !preview) return;

    try {
      setImportSuccess(false);
      const imported = await importAgent(shareToken);

      if (imported) {
        setImportSuccess(true);
        onImportSuccess?.(imported.agent_name);

        // Close dialog after 2 seconds
        setTimeout(() => {
          onClose();
        }, 2000);
      }
    } catch (err) {
      logger.error('Error importing agent:', err);
    }
  };

  // Extract category from template slug
  const category = preview?.template_slug.split('-')[0];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Agent Preview
          </DialogTitle>
          <DialogDescription>
            Preview agent configuration before importing
          </DialogDescription>
        </DialogHeader>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Preview Content */}
        {!loading && !error && preview && (
          <div className="space-y-4">
            {/* Agent Info */}
            <div className="rounded-lg border p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg flex items-center gap-2">
                    {preview.agent_name}
                    {category && (
                      <Badge variant="secondary" className="capitalize">
                        {category}
                      </Badge>
                    )}
                  </h3>
                  <div className="flex items-center gap-2 mt-2 text-sm text-muted-foreground">
                    <User className="h-3 w-3" />
                    Created by {preview.creator_display_name}
                  </div>
                  {preview.customizations_summary && (
                    <p className="text-sm text-muted-foreground mt-2">
                      {preview.customizations_summary}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Import Success */}
            {importSuccess && (
              <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-600">
                  Agent imported successfully! Closing...
                </AlertDescription>
              </Alert>
            )}

            {/* Import Error */}
            {importError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{importError}</AlertDescription>
              </Alert>
            )}

            {/* Configuration Tabs */}
            <div className="rounded-lg border">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-5">
                  <TabsTrigger value="instructions" className="gap-2">
                    <FileText className="h-4 w-4" />
                    <span className="hidden sm:inline">Instructions</span>
                  </TabsTrigger>
                  <TabsTrigger value="rules" className="gap-2">
                    <ListChecks className="h-4 w-4" />
                    <span className="hidden sm:inline">Rules</span>
                  </TabsTrigger>
                  <TabsTrigger value="capabilities" className="gap-2">
                    <Settings2 className="h-4 w-4" />
                    <span className="hidden sm:inline">Capabilities</span>
                  </TabsTrigger>
                  <TabsTrigger value="output" className="gap-2">
                    <FileOutput className="h-4 w-4" />
                    <span className="hidden sm:inline">Output</span>
                  </TabsTrigger>
                  <TabsTrigger value="tools" className="gap-2">
                    <Wrench className="h-4 w-4" />
                    <span className="hidden sm:inline">Tools</span>
                  </TabsTrigger>
                </TabsList>

                {/* Instructions Tab */}
                <TabsContent value="instructions" className="p-4 space-y-2">
                  <h4 className="font-semibold text-sm">System Prompt</h4>
                  <div className="rounded-md bg-muted p-4 max-h-[300px] overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">
                      {preview.configuration_preview.system_prompt || 'No instructions provided'}
                    </pre>
                  </div>
                </TabsContent>

                {/* Rules Tab */}
                <TabsContent value="rules" className="p-4 space-y-2">
                  <h4 className="font-semibold text-sm">Agent Rules</h4>
                  <div className="rounded-md bg-muted p-4 max-h-[300px] overflow-y-auto">
                    {preview.configuration_preview.rules &&
                    preview.configuration_preview.rules.length > 0 ? (
                      <ul className="space-y-2">
                        {preview.configuration_preview.rules.map((rule, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm">
                            <span className="text-primary">•</span>
                            <span>{rule}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-muted-foreground">No rules defined</p>
                    )}
                  </div>
                </TabsContent>

                {/* Capabilities Tab */}
                <TabsContent value="capabilities" className="p-4 space-y-2">
                  <h4 className="font-semibold text-sm">Agent Capabilities (JSON)</h4>
                  <div className="rounded-md bg-muted p-4 max-h-[300px] overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">
                      {JSON.stringify(preview.configuration_preview.capabilities, null, 2)}
                    </pre>
                  </div>
                </TabsContent>

                {/* Output Format Tab */}
                <TabsContent value="output" className="p-4 space-y-2">
                  <h4 className="font-semibold text-sm">Output Format</h4>
                  <div className="rounded-md bg-muted p-4 max-h-[300px] overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-mono text-xs">
                      {preview.configuration_preview.output_format ||
                        'No output format specified'}
                    </pre>
                  </div>
                </TabsContent>

                {/* Tools Tab */}
                <TabsContent value="tools" className="p-4 space-y-2">
                  <h4 className="font-semibold text-sm">
                    Available Tools ({preview.configuration_preview.tools.length})
                  </h4>
                  <div className="rounded-md bg-muted p-4 max-h-[300px] overflow-y-auto">
                    <div className="flex flex-wrap gap-2">
                      {preview.configuration_preview.tools.map((tool, idx) => (
                        <Badge key={idx} variant="outline" className="font-mono text-xs">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
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

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={onClose} className="gap-2">
            <X className="h-4 w-4" />
            Close
          </Button>

          {preview && preview.can_import && !importSuccess && (
            <Button
              onClick={handleImport}
              disabled={importing || loading}
              className="gap-2"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Import Agent
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SharedAgentPreview;
