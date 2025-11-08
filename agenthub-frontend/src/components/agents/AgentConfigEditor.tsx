/**
 * Agent Configuration Editor Component
 *
 * Tabbed markdown editor for customizing agent configuration.
 * Supports editing: instructions (system_prompt), rules, capabilities, output_format.
 *
 * @module components/agents/AgentConfigEditor
 * @version 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  Save,
  RotateCcw,
  AlertCircle,
  CheckCircle,
  Loader2,
  FileText,
  ListChecks,
  Settings2,
  FileOutput,
  Eye,
  Code,
} from 'lucide-react';
import { useUserAgentInstances } from '../../hooks/useAgentManagement';
import type { UserAgentInstance, UpdateInstanceRequest } from '../../types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Textarea } from '../ui/textarea';
import { Alert, AlertDescription } from '../ui/alert';
import { Separator } from '../ui/separator';
import logger from '../../utils/logger';

interface AgentConfigEditorProps {
  instance: UserAgentInstance;
  onSave?: (updatedInstance: UserAgentInstance) => void;
  onCancel?: () => void;
}

/**
 * Agent Configuration Editor
 * Allows editing agent configuration with markdown support
 */
export const AgentConfigEditor: React.FC<AgentConfigEditorProps> = ({
  instance,
  onSave,
  onCancel,
}) => {
  const { updateInstance, isLoading: loading, error } = useUserAgentInstances();

  // Local state for editing
  const [systemPrompt, setSystemPrompt] = useState(instance.system_prompt || '');
  const [rules, setRules] = useState<string[]>(instance.rules || []);
  const [capabilities, setCapabilities] = useState(
    JSON.stringify(instance.capabilities || {}, null, 2)
  );
  const [outputFormat, setOutputFormat] = useState(instance.output_format || '');

  // UI state
  const [activeTab, setActiveTab] = useState('instructions');
  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);

  // Convert rules array to markdown string
  const rulesText = rules.join('\n');

  // Track changes
  useEffect(() => {
    const changed =
      systemPrompt !== (instance.system_prompt || '') ||
      rulesText !== (instance.rules || []).join('\n') ||
      capabilities !== JSON.stringify(instance.capabilities || {}, null, 2) ||
      outputFormat !== (instance.output_format || '');

    setHasChanges(changed);
  }, [systemPrompt, rulesText, capabilities, outputFormat, instance]);

  // Handle save
  const handleSave = async () => {
    try {
      setSaveSuccess(false);

      // Parse capabilities JSON
      let parsedCapabilities;
      try {
        parsedCapabilities = JSON.parse(capabilities);
      } catch (e) {
        logger.error('Invalid JSON in capabilities:', e);
        return;
      }

      // Parse rules (split by newlines, filter empty)
      const parsedRules = rulesText
        .split('\n')
        .map(r => r.trim())
        .filter(r => r.length > 0);

      const updateData: UpdateInstanceRequest = {
        system_prompt: systemPrompt,
        rules: parsedRules.length > 0 ? parsedRules : undefined,
        capabilities: parsedCapabilities,
        output_format: outputFormat || undefined,
      };

      const updated = await updateInstance(instance.id, updateData);

      if (updated) {
        setSaveSuccess(true);
        setHasChanges(false);
        onSave?.(updated);

        // Clear success message after 3 seconds
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } catch (err) {
      logger.error('Error saving configuration:', err);
    }
  };

  // Handle reset
  const handleReset = () => {
    setSystemPrompt(instance.system_prompt || '');
    setRules(instance.rules || []);
    setCapabilities(JSON.stringify(instance.capabilities || {}, null, 2));
    setOutputFormat(instance.output_format || '');
    setHasChanges(false);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                {instance.agent_name}
                {instance.is_customized && (
                  <Badge variant="secondary">Customized</Badge>
                )}
              </CardTitle>
              <CardDescription className="mt-2">
                Edit configuration using markdown format. Changes are saved to your instance.
              </CardDescription>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-2">
              <Button
                variant={previewMode ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPreviewMode(!previewMode)}
                className="gap-2"
              >
                {previewMode ? (
                  <>
                    <Eye className="h-4 w-4" />
                    Preview
                  </>
                ) : (
                  <>
                    <Code className="h-4 w-4" />
                    Edit
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Success Message */}
      {saveSuccess && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">
            Configuration saved successfully!
          </AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Editor Tabs */}
      <Card>
        <CardContent className="pt-6">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="instructions" className="gap-2">
                <FileText className="h-4 w-4" />
                Instructions
              </TabsTrigger>
              <TabsTrigger value="rules" className="gap-2">
                <ListChecks className="h-4 w-4" />
                Rules
              </TabsTrigger>
              <TabsTrigger value="capabilities" className="gap-2">
                <Settings2 className="h-4 w-4" />
                Capabilities
              </TabsTrigger>
              <TabsTrigger value="output" className="gap-2">
                <FileOutput className="h-4 w-4" />
                Output Format
              </TabsTrigger>
            </TabsList>

            {/* Instructions Tab */}
            <TabsContent value="instructions" className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-2">System Prompt (Instructions)</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  The main instructions that define the agent's behavior and personality.
                  Supports markdown formatting.
                </p>

                {previewMode ? (
                  <div className="rounded-md border p-4 min-h-[400px] prose prose-sm dark:prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap font-mono text-sm">
                      {systemPrompt || 'No instructions set'}
                    </pre>
                  </div>
                ) : (
                  <Textarea
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    placeholder="Enter agent instructions in markdown format..."
                    className="min-h-[400px] font-mono text-sm"
                  />
                )}
              </div>
            </TabsContent>

            {/* Rules Tab */}
            <TabsContent value="rules" className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-2">Agent Rules</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  One rule per line. These define specific behaviors and constraints for the agent.
                </p>

                {previewMode ? (
                  <div className="rounded-md border p-4 min-h-[400px]">
                    {rulesText ? (
                      <ul className="space-y-2">
                        {rulesText.split('\n').filter(r => r.trim()).map((rule, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-primary">•</span>
                            <span className="text-sm">{rule}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted-foreground text-sm">No rules set</p>
                    )}
                  </div>
                ) : (
                  <Textarea
                    value={rulesText}
                    onChange={(e) => setRules(e.target.value.split('\n'))}
                    placeholder="Enter one rule per line..."
                    className="min-h-[400px] font-mono text-sm"
                  />
                )}
              </div>
            </TabsContent>

            {/* Capabilities Tab */}
            <TabsContent value="capabilities" className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-2">Capabilities (JSON)</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Define agent capabilities as JSON. Used for feature flags and advanced configuration.
                </p>

                {previewMode ? (
                  <div className="rounded-md border p-4 min-h-[400px]">
                    <pre className="text-sm font-mono whitespace-pre-wrap">
                      {capabilities || '{}'}
                    </pre>
                  </div>
                ) : (
                  <Textarea
                    value={capabilities}
                    onChange={(e) => setCapabilities(e.target.value)}
                    placeholder='{"feature": true, "max_tokens": 4000}'
                    className="min-h-[400px] font-mono text-sm"
                  />
                )}
              </div>
            </TabsContent>

            {/* Output Format Tab */}
            <TabsContent value="output" className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold mb-2">Output Format</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Define how the agent should format its responses. Supports markdown templates.
                </p>

                {previewMode ? (
                  <div className="rounded-md border p-4 min-h-[400px]">
                    <pre className="whitespace-pre-wrap font-mono text-sm">
                      {outputFormat || 'No output format specified'}
                    </pre>
                  </div>
                ) : (
                  <Textarea
                    value={outputFormat}
                    onChange={(e) => setOutputFormat(e.target.value)}
                    placeholder="Enter output format template..."
                    className="min-h-[400px] font-mono text-sm"
                  />
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {hasChanges && (
                <Badge variant="outline" className="gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Unsaved Changes
                </Badge>
              )}
            </div>

            <div className="flex gap-2">
              {onCancel && (
                <Button variant="outline" onClick={onCancel}>
                  Cancel
                </Button>
              )}

              <Button
                variant="outline"
                onClick={handleReset}
                disabled={!hasChanges || loading}
                className="gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>

              <Button
                onClick={handleSave}
                disabled={!hasChanges || loading}
                className="gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Configuration Metadata</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Instance ID:</span>
            <code className="text-xs">{instance.id}</code>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Template:</span>
            <span>{instance.agent_name}</span>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Customized:</span>
            <Badge variant={instance.is_customized ? 'default' : 'outline'}>
              {instance.is_customized ? 'Yes' : 'No'}
            </Badge>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Tools:</span>
            <span className="text-xs">{instance.tools?.length || 0} configured</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AgentConfigEditor;
