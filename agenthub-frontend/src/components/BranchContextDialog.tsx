import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { GitBranch, Edit, Copy, Check as CheckIcon, ChevronDown, ChevronUp } from "lucide-react";
import { getBranchContext } from "../api";
import logger from "../utils/logger";

interface BranchContextDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClose: () => void;
  branchId: string;
}

export const BranchContextDialog: React.FC<BranchContextDialogProps> = ({
  open,
  onOpenChange,
  onClose,
  branchId
}) => {
  const [branchContext, setBranchContext] = useState<any>(null);
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [jsonCopied, setJsonCopied] = useState(false);
  const [rawJsonExpanded, setRawJsonExpanded] = useState(false);

  // Fetch branch context when dialog opens
  useEffect(() => {
    if (open && branchId) {
      fetchBranchContext();
    } else {
      setEditMode(false);
      setBranchContext(null);
    }
  }, [open, branchId]);

  const fetchBranchContext = async () => {
    setLoading(true);
    try {
      const context = await getBranchContext(branchId);
      logger.debug('Fetched branch context:', context);
      
      if (context) {
        setBranchContext(context);
      }
    } catch (error) {
      logger.error('Error fetching branch context:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyJsonToClipboard = () => {
    if (branchContext) {
      const jsonString = JSON.stringify(branchContext, null, 2);
      navigator.clipboard.writeText(jsonString).then(() => {
        setJsonCopied(true);
        setTimeout(() => setJsonCopied(false), 2000);
      }).catch(err => {
        logger.error('Failed to copy JSON:', err);
      });
    }
  };

  // Get level-based styling
  const getLevelStyling = (depth: number) => {
    const styles = [
      { // Level 0 - Root level fields
        bg: 'bg-blue-50 dark:bg-blue-900/10',
        border: 'border-l-4 border-blue-500',
        text: 'text-blue-900 dark:text-blue-100',
        keySize: 'text-base font-semibold',
        padding: 'pl-3',
      },
      { // Level 1
        bg: 'bg-green-50 dark:bg-green-900/10',
        border: 'border-l-4 border-green-500',
        text: 'text-green-900 dark:text-green-100',
        keySize: 'text-sm font-medium',
        padding: 'pl-6',
      },
      { // Level 2
        bg: 'bg-purple-50 dark:bg-purple-900/10',
        border: 'border-l-4 border-purple-500',
        text: 'text-purple-900 dark:text-purple-100',
        keySize: 'text-sm',
        padding: 'pl-9',
      },
      { // Level 3+
        bg: 'bg-orange-50 dark:bg-orange-900/10',
        border: 'border-l-4 border-orange-500',
        text: 'text-orange-900 dark:text-orange-100',
        keySize: 'text-xs',
        padding: 'pl-12',
      },
    ];
    
    return styles[Math.min(depth, styles.length - 1)];
  };

  // Render nested data with level-based styling
  const renderNestedData = (data: any, depth: number = 0): React.ReactElement => {
    const style = getLevelStyling(depth);
    
    if (data === null || data === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }
    
    if (typeof data === 'string' || typeof data === 'number' || typeof data === 'boolean') {
      return <span className={style.text}>{String(data)}</span>;
    }
    
    if (Array.isArray(data)) {
      return (
        <div className="space-y-1">
          {data.map((item, index) => (
            <div key={index} className={`${style.padding} py-1`}>
              <span className={`${style.text} ${style.keySize}`}>[{index}]:</span>
              <div className="ml-4">
                {renderNestedData(item, depth + 1)}
              </div>
            </div>
          ))}
        </div>
      );
    }
    
    if (typeof data === 'object') {
      return (
        <div className="space-y-2">
          {Object.entries(data).map(([key, value]) => (
            <div
              key={key}
              className={`${style.bg} ${style.border} ${style.padding} py-2 rounded-r transition-colors hover:opacity-90`}
            >
              <div>
                <span className={`${style.text} ${style.keySize} capitalize`}>
                  {key.replace(/_/g, ' ')}:
                </span>
                {typeof value === 'object' && value !== null ? (
                  <div className="mt-2">
                    {renderNestedData(value, depth + 1)}
                  </div>
                ) : (
                  <span className="ml-2">{renderNestedData(value, depth + 1)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    }
    
    return <span>{String(data)}</span>;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] h-[90vh] max-w-[90vw] max-h-[90vh] overflow-hidden bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl text-left flex items-center gap-2">
            <GitBranch className="w-5 h-5" />
            Branch Context
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading branch context...</p>
            </div>
          ) : branchContext ? (
            <div className="space-y-4 p-4">
              {/* Context Header */}
              <div className="bg-surface-hover rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <GitBranch className="w-5 h-5" /> 
                  Branch Context Data
                </h3>
                
                {/* Render nested data with level-based styling */}
                <div className="space-y-2">
                  {renderNestedData(branchContext.data || branchContext)}
                </div>
                
                {/* Raw JSON Section with expand/collapse and copy */}
                <div className="mt-6 border-t pt-4">
                  <div className="flex items-center justify-between mb-2">
                    <button
                      onClick={() => setRawJsonExpanded(!rawJsonExpanded)}
                      className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
                    >
                      {rawJsonExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                      View Complete JSON Context
                    </button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={copyJsonToClipboard}
                      className="flex items-center gap-2"
                    >
                      {jsonCopied ? (
                        <>
                          <CheckIcon className="w-4 h-4" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-4 h-4" />
                          Copy JSON
                        </>
                      )}
                    </Button>
                  </div>
                  
                  {rawJsonExpanded && (
                    <div className="mt-3 bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
                      <pre className="text-xs overflow-x-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                        {JSON.stringify(branchContext, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <GitBranch className="w-12 h-12 text-gray-400 dark:text-gray-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No Branch Context Available</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Branch context has not been initialized yet.
              </p>
              <Button 
                variant="default" 
                className="mt-4"
                onClick={() => {
                  // Initialize with empty values
                  setBranchContext({
                    data: {
                      branch_info: {},
                      branch_workflow: {},
                      feature_flags: {},
                      discovered_patterns: {},
                      branch_decisions: {},
                      branch_settings: {},
                      active_patterns: {},
                      local_overrides: {},
                      delegation_rules: {}
                    }
                  });
                  setEditMode(true);
                }}
              >
                <Edit className="w-4 h-4 mr-2" />
                Initialize Branch Context
              </Button>
            </div>
          )}
        </div>
        <DialogFooter>
          {!editMode && (
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default BranchContextDialog;