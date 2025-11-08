import { Card } from '../../ui/card';
import CommandBox from '../shared/CommandBox';
import { Webhook } from 'lucide-react';

interface ClaudeHooksProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const ClaudeHooks = ({ expandedSections, toggleSection }: ClaudeHooksProps) => {
  const sectionData = {
    id: 'claude-hooks',
    title: 'Claude Code Hook System',
    description: 'Intelligent automation and file system protection for Claude Code development',
    icon: <Webhook className="h-6 w-6 text-indigo-500" />,
    content: (
      <div className="space-y-6">
        <div>
          <h4 className="text-lg font-semibold mb-3">What Are Claude Code Hooks?</h4>
          <Card className="p-4 bg-indigo-50 dark:bg-indigo-950 border-indigo-200 dark:border-indigo-800">
            <p className="text-sm text-indigo-900 dark:text-indigo-100 mb-3">
              <strong>Claude Code hooks</strong> are Python scripts that automatically run before and after tool execution,
              providing intelligent automation, file protection, and workflow guidance for AI development.
            </p>
            <div className="text-sm text-indigo-800 dark:text-indigo-200 space-y-2">
              <p><strong>Key Capabilities:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li>File system protection (prevents accidental dangerous operations)</li>
                <li>Documentation enforcement and automatic indexing</li>
                <li>Workflow hints and intelligent guidance</li>
                <li>Security protection (blocks .env file access)</li>
                <li>Automatic session tracking (2-hour work sessions)</li>
                <li>Context injection and MCP task interception</li>
              </ul>
            </div>
          </Card>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Hook System Architecture</h4>
          <div className="space-y-3">
            <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                📋 Pre-Tool Hook (pre_tool_use.py)
              </h5>
              <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                <p><strong>Runs BEFORE tool execution:</strong></p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Validates file creation in project root (only allowed files)</li>
                  <li>Blocks .env file access (security protection)</li>
                  <li>Prevents dangerous commands (rm -rf /, format operations)</li>
                  <li>Checks documentation requirements for important files</li>
                  <li>Enforces tool permissions (Dynamic Tool Enforcement v2.0)</li>
                  <li>Generates workflow guidance hints</li>
                </ul>
              </div>
            </Card>

            <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">
                ✅ Post-Tool Hook (post_tool_use.py)
              </h5>
              <div className="text-sm text-green-800 dark:text-green-200 space-y-2">
                <p><strong>Runs AFTER tool execution:</strong></p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Updates documentation index (ai_docs/index.json) automatically</li>
                  <li>Synchronizes context with MCP backend</li>
                  <li>Tracks agent state changes (call_agent responses)</li>
                  <li>Generates post-action hints and insights</li>
                  <li>Logs all tool executions for audit trails</li>
                </ul>
              </div>
            </Card>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">File System Protection Rules</h4>
          <div className="space-y-3">
            <Card className="p-4 bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800">
              <h5 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">
                🔒 Root Directory Restrictions
              </h5>
              <div className="text-sm text-orange-800 dark:text-orange-200 space-y-2">
                <p><strong>Protected:</strong></p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Only 5 .md files allowed in project root: README.md, CHANGELOG.md, TEST-CHANGELOG.md, CLAUDE.md, CLAUDE.local.md</li>
                  <li>All documentation must go in <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">ai_docs/</code> folder</li>
                  <li>Test files must be in <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">agenthub_main/src/tests/</code></li>
                  <li>Scripts must be in <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">scripts/</code> or <code className="bg-orange-100 dark:bg-orange-900 px-1 rounded">docker-system/</code></li>
                  <li>ai_docs subfolders must use kebab-case (lowercase-with-dashes)</li>
                </ul>
              </div>
            </Card>

            <Card className="p-4 bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800">
              <h5 className="font-semibold text-red-900 dark:text-red-100 mb-2">
                ⛔ Security Protection
              </h5>
              <div className="text-sm text-red-800 dark:text-red-200 space-y-2">
                <p><strong>Blocked Operations:</strong></p>
                <ul className="list-disc list-inside ml-4 space-y-1">
                  <li>Reading or creating .env files (except .env.sample, .env.example, .env.template)</li>
                  <li>Dangerous rm commands: <code className="bg-red-100 dark:bg-red-900 px-1 rounded">rm -rf /</code>, <code className="bg-red-100 dark:bg-red-900 px-1 rounded">sudo rm</code></li>
                  <li>System format commands: <code className="bg-red-100 dark:bg-red-900 px-1 rounded">mkfs</code>, <code className="bg-red-100 dark:bg-red-900 px-1 rounded">dd of=/dev</code></li>
                  <li>Dangerous permission changes: <code className="bg-red-100 dark:bg-red-900 px-1 rounded">chmod 777 /etc</code></li>
                </ul>
              </div>
            </Card>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Documentation System</h4>
          <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
            <h5 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">
              📚 Selective Documentation Enforcement
            </h5>
            <div className="text-sm text-purple-800 dark:text-purple-200 space-y-2">
              <p><strong>How it works:</strong></p>
              <ul className="list-disc list-inside ml-4 space-y-1">
                <li><strong>_absolute_docs Pattern:</strong> Files with docs in <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">ai_docs/_absolute_docs/</code> are marked as "important"</li>
                <li><strong>Smart Blocking:</strong> Only blocks modifications to files WITH existing documentation</li>
                <li><strong>Session Tracking:</strong> 2-hour sessions prevent workflow disruption (first access blocks, subsequent allowed)</li>
                <li><strong>Auto-Indexing:</strong> Changes to ai_docs automatically update <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">index.json</code></li>
                <li><strong>Obsolete Tracking:</strong> Moves docs to <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">_obsolete_docs/</code> when source files deleted</li>
                <li><strong>Folder Marking:</strong> <code className="bg-purple-100 dark:bg-purple-900 px-1 rounded">f_index.md</code> marks entire folders as important</li>
              </ul>
            </div>
          </Card>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Hook System Files</h4>
          <div className="space-y-3">
            <CommandBox
              command="ls -la .claude/hooks/"
              title="View Hook System Files"
              description="Located in .claude/hooks/ directory"
            />
            <div className="grid md:grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
                <strong className="text-gray-900 dark:text-gray-100">Core Hooks:</strong>
                <ul className="mt-2 space-y-1 text-gray-600 dark:text-gray-400">
                  <li>• pre_tool_use.py</li>
                  <li>• post_tool_use.py</li>
                  <li>• session_start_hook.py</li>
                </ul>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
                <strong className="text-gray-900 dark:text-gray-100">Utilities:</strong>
                <ul className="mt-2 space-y-1 text-gray-600 dark:text-gray-400">
                  <li>• utils/session_tracker.py</li>
                  <li>• utils/docs_indexer.py</li>
                  <li>• utils/env_loader.py</li>
                  <li>• utils/agent_state_manager.py</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Configuration Files</h4>
          <div className="space-y-3">
            <CommandBox
              command="cat .claude/hooks/config/__claude_hook__allowed_root_files"
              title="View Allowed Root Files"
              description="Lists files permitted in project root"
            />
            <CommandBox
              command="cat .claude/hooks/config/__claude_hook__valid_test_paths"
              title="View Valid Test Paths"
              description="Lists directories where test files can be created"
            />
            <CommandBox
              command="cat .claude/hooks/config/__claude_hook__valid_env_paths"
              title="View Valid .env Paths"
              description="Lists directories where .env files can be created (default: root only)"
            />
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Manual Operations</h4>
          <div className="space-y-3">
            <CommandBox
              command="python .claude/hooks/utils/docs_indexer.py"
              title="Update Documentation Index"
              description="Manually regenerate ai_docs/index.json"
            />
            <CommandBox
              command="ls -la ai_docs/_absolute_docs/"
              title="View Important Files Documentation"
              description="See which files have documentation and are protected"
            />
            <CommandBox
              command="ls -la ai_docs/_obsolete_docs/"
              title="View Obsolete Documentation"
              description="See archived documentation from deleted source files"
            />
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Understanding Hook Messages</h4>
          <Card className="p-4 bg-gray-50 dark:bg-gray-900">
            <div className="text-sm text-gray-700 dark:text-gray-300 space-y-3">
              <div>
                <strong className="text-red-600 dark:text-red-400">⚠️ BLOCKED:</strong>
                <p className="ml-4 mt-1">Operation prevented for safety (file protection, dangerous commands, security violations)</p>
              </div>
              <div>
                <strong className="text-yellow-600 dark:text-yellow-400">💡 Workflow Guidance:</strong>
                <p className="ml-4 mt-1">Intelligent hints about next steps, best practices, or potential issues</p>
              </div>
              <div>
                <strong className="text-blue-600 dark:text-blue-400">📋 Previous Action Insights:</strong>
                <p className="ml-4 mt-1">Contextual information from previous operations to maintain workflow continuity</p>
              </div>
              <div>
                <strong className="text-purple-600 dark:text-purple-400">📚 Documentation Required:</strong>
                <p className="ml-4 mt-1">Important file needs documentation update (first access in session)</p>
              </div>
            </div>
          </Card>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Best Practices</h4>
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">✅ Do</h5>
              <ul className="text-sm text-green-800 dark:text-green-200 space-y-1 list-disc list-inside">
                <li>Organize documentation in ai_docs subfolders</li>
                <li>Use kebab-case for folder names</li>
                <li>Create absolute docs for important files</li>
                <li>Follow hook guidance messages</li>
                <li>Use .env.sample for example configurations</li>
                <li>Place tests in correct directories</li>
              </ul>
            </Card>

            <Card className="p-4 bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800">
              <h5 className="font-semibold text-red-900 dark:text-red-100 mb-2">❌ Don't</h5>
              <ul className="text-sm text-red-800 dark:text-red-200 space-y-1 list-disc list-inside">
                <li>Create loose .md files in project root</li>
                <li>Try to read or create .env files directly</li>
                <li>Use uppercase in ai_docs folder names</li>
                <li>Ignore documentation warnings</li>
                <li>Create test files outside valid paths</li>
                <li>Run dangerous system commands</li>
              </ul>
            </Card>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Hook System Benefits</h4>
          <div className="grid md:grid-cols-3 gap-3">
            <Card className="p-3 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <h5 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">🛡️ Safety</h5>
              <p className="text-xs text-blue-800 dark:text-blue-200">
                Prevents accidental dangerous operations and protects sensitive files
              </p>
            </Card>
            <Card className="p-3 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
              <h5 className="text-sm font-semibold text-purple-900 dark:text-purple-100 mb-2">📚 Organization</h5>
              <p className="text-xs text-purple-800 dark:text-purple-200">
                Maintains clean project structure and automatic documentation
              </p>
            </Card>
            <Card className="p-3 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
              <h5 className="text-sm font-semibold text-green-900 dark:text-green-100 mb-2">💡 Guidance</h5>
              <p className="text-xs text-green-800 dark:text-green-200">
                Provides intelligent workflow hints and best practice recommendations
              </p>
            </Card>
          </div>
        </div>
      </div>
    ),
    isExpanded: expandedSections['claude-hooks'],
    onToggle: () => toggleSection('claude-hooks')
  };

  return sectionData;
};

export default ClaudeHooks;
