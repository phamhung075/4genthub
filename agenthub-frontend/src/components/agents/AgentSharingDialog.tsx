/**
 * Agent Sharing Dialog Component
 *
 * Dialog for sharing/unsharing agents with copy-to-clipboard functionality.
 * Generates secure share tokens and provides shareable URLs.
 *
 * @module components/agents/AgentSharingDialog
 * @version 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  Share2,
  Lock,
  Globe,
  Copy,
  Check,
  AlertCircle,
  ExternalLink,
  Loader2,
  X,
} from 'lucide-react';
import { useAgentSharing } from '../../hooks/useAgentManagement';
import type { UserAgentInstance, ShareAgentResponse } from '../../types';
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
import { Alert, AlertDescription } from '../ui/alert';
import { Separator } from '../ui/separator';
import logger from '../../utils/logger';

interface AgentSharingDialogProps {
  instance: UserAgentInstance | null;
  isOpen: boolean;
  onClose: () => void;
  onShareSuccess?: (response: ShareAgentResponse) => void;
  onUnshareSuccess?: (instanceId: string) => void;
}

/**
 * Agent Sharing Dialog
 * Handles agent sharing with copy-to-clipboard and privacy controls
 */
export const AgentSharingDialog: React.FC<AgentSharingDialogProps> = ({
  instance,
  isOpen,
  onClose,
  onShareSuccess,
  onUnshareSuccess,
}) => {
  const { shareAgent, unshareAgent, loading, error } = useAgentSharing();

  // Local state
  const [shareResponse, setShareResponse] = useState<ShareAgentResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Check if already shared
  const isShared = instance?.visibility === 'public';

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (!isOpen) {
      setShareResponse(null);
      setCopied(false);
      setActionSuccess(null);
    }
  }, [isOpen]);

  // Handle share
  const handleShare = async () => {
    if (!instance) return;

    try {
      setActionSuccess(null);
      const response = await shareAgent(instance.id);

      if (response) {
        setShareResponse(response);
        setActionSuccess('Agent shared successfully!');
        onShareSuccess?.(response);

        // Clear success message after 3 seconds
        setTimeout(() => setActionSuccess(null), 3000);
      }
    } catch (err) {
      logger.error('Error sharing agent:', err);
    }
  };

  // Handle unshare
  const handleUnshare = async () => {
    if (!instance) return;

    try {
      setActionSuccess(null);
      const success = await unshareAgent(instance.id);

      if (success) {
        setShareResponse(null);
        setActionSuccess('Agent is now private');
        onUnshareSuccess?.(instance.id);

        // Clear success message after 3 seconds
        setTimeout(() => setActionSuccess(null), 3000);
      }
    } catch (err) {
      logger.error('Error unsharing agent:', err);
    }
  };

  // Copy to clipboard
  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);

      // Reset copied state after 2 seconds
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      logger.error('Failed to copy to clipboard:', err);
    }
  };

  if (!instance) return null;

  const shareUrl = shareResponse?.shareable_url || '';

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            Share Agent
          </DialogTitle>
          <DialogDescription>
            Make your customized agent available to others in the marketplace
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Agent Info */}
          <div className="rounded-lg border p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{instance.agent_name}</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {instance.system_prompt?.substring(0, 100)}
                  {instance.system_prompt && instance.system_prompt.length > 100 && '...'}
                </p>
              </div>
              <Badge variant={isShared ? 'default' : 'outline'} className="gap-1">
                {isShared ? (
                  <>
                    <Globe className="h-3 w-3" />
                    Public
                  </>
                ) : (
                  <>
                    <Lock className="h-3 w-3" />
                    Private
                  </>
                )}
              </Badge>
            </div>
          </div>

          {/* Success Message */}
          {actionSuccess && (
            <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
              <Check className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-600">
                {actionSuccess}
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

          {/* Share Info */}
          {(isShared || shareResponse) && shareUrl && (
            <div className="space-y-3">
              <Separator />

              <div>
                <label className="text-sm font-medium">Shareable URL</label>
                <div className="flex gap-2 mt-2">
                  <div className="flex-1 rounded-md border bg-muted p-2">
                    <code className="text-xs break-all">{shareUrl}</code>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleCopy(shareUrl)}
                    className="gap-2 shrink-0"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 text-green-600" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {shareResponse?.share_token && (
                <div>
                  <label className="text-sm font-medium">Share Token</label>
                  <div className="flex gap-2 mt-2">
                    <div className="flex-1 rounded-md border bg-muted p-2">
                      <code className="text-xs break-all">
                        {shareResponse.share_token}
                      </code>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(shareResponse.share_token)}
                      className="gap-2 shrink-0"
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}

              <div className="flex items-start gap-2 p-3 rounded-md bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
                <AlertCircle className="h-4 w-4 text-blue-600 mt-0.5" />
                <div className="text-sm text-blue-600 dark:text-blue-400">
                  <p className="font-medium">Sharing Information</p>
                  <ul className="mt-1 space-y-1 text-xs">
                    <li>• Others can import your agent configuration</li>
                    <li>• They get a copy - your original remains unchanged</li>
                    <li>• You can unshare at any time</li>
                    <li>• Existing imports will continue to work</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Not Shared Info */}
          {!isShared && !shareResponse && (
            <div className="space-y-3">
              <Separator />

              <div className="flex items-start gap-2 p-3 rounded-md bg-muted">
                <Lock className="h-4 w-4 text-muted-foreground mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium">Private Agent</p>
                  <p className="text-muted-foreground mt-1">
                    This agent is currently private. Share it to make it available in the
                    marketplace for others to discover and import.
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <p className="font-medium">What happens when you share:</p>
                <ul className="space-y-1 text-muted-foreground ml-4">
                  <li>• A secure share link will be generated</li>
                  <li>• Your agent appears in the public marketplace</li>
                  <li>• Others can import a copy of your configuration</li>
                  <li>• Your original agent remains under your control</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={onClose} className="gap-2">
            <X className="h-4 w-4" />
            Close
          </Button>

          {isShared || shareResponse ? (
            <>
              {shareUrl && (
                <Button
                  variant="outline"
                  onClick={() => window.open(shareUrl, '_blank')}
                  className="gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  View in Marketplace
                </Button>
              )}
              <Button
                variant="destructive"
                onClick={handleUnshare}
                disabled={loading}
                className="gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4" />
                    Make Private
                  </>
                )}
              </Button>
            </>
          ) : (
            <Button
              onClick={handleShare}
              disabled={loading}
              className="gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Sharing...
                </>
              ) : (
                <>
                  <Globe className="h-4 w-4" />
                  Share to Marketplace
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AgentSharingDialog;
