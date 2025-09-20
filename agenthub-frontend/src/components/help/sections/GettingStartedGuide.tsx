import React from 'react';
import { Card } from '../../ui/card';
import CommandBox from '../shared/CommandBox';
import { Play, Zap } from 'lucide-react';

interface GettingStartedGuideProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const GettingStartedGuide: React.FC<GettingStartedGuideProps> = ({ expandedSections, toggleSection }) => {
  const sectionData = {
    id: 'getting-started',
    title: 'Getting Started Guide',
    description: '3-minute quick start with automated setup script - simplified configuration process',
    icon: <Play className="h-6 w-6 text-green-500" />,
    content: (
      <div className="space-y-6">
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 p-6 rounded-lg border border-blue-200 dark:border-blue-800 mb-6">
          <h3 className="text-xl font-bold mb-2 text-blue-900 dark:text-blue-100">⚡ 3-Minute Quick Start with Automated Setup</h3>
          <p className="text-blue-800 dark:text-blue-200">
            Get started with 4genthub in just 3 minutes using our <strong>automated setup script</strong> - handles all configuration automatically with clear prompts!
          </p>
          <div className="mt-2 p-2 bg-white/50 dark:bg-black/50 rounded">
            <code className="text-sm font-mono text-blue-900 dark:text-blue-100">
              python3 .claude/hooks/setup_hooks.py
            </code>
            <span className="text-xs text-blue-700 dark:text-blue-300 ml-2">← One command does it all!</span>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Installation Steps</h4>
          <div className="space-y-4">
            <Card className="p-4 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Step 1: Create 4genthub Account</h5>
              <div className="space-y-3">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  Register for free at the 4genthub hosted service:
                </p>
                <ol className="list-decimal list-inside text-sm text-blue-800 dark:text-blue-200 space-y-1 ml-4">
                  <li>Register at <a href="https://www.4genthub.com" target="_blank" rel="noopener noreferrer" className="underline font-semibold">https://www.4genthub.com</a></li>
                  <li>Complete account verification via email</li>
                  <li>Navigate to Dashboard → API Tokens</li>
                  <li>Generate new API token and copy it</li>
                </ol>
                <div className="bg-blue-100 dark:bg-blue-900 p-3 rounded-lg mt-3">
                  <p className="text-xs font-semibold text-blue-900 dark:text-blue-100">✅ No server setup required - fully hosted service!</p>
                </div>
              </div>
            </Card>

            <Card className="p-4 border-l-4 border-green-500 bg-green-50 dark:bg-green-950">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Step 2: Install Python 3.12</h5>
              <div className="space-y-3">
                <p className="text-sm text-green-800 dark:text-green-200 mb-3">
                  4genthub requires Python 3.12 (exact version) for the client hooks:
                </p>

                <div className="space-y-2">
                  <div className="text-sm font-semibold text-green-900 dark:text-green-100">Linux (Ubuntu/Debian):</div>
                  <CommandBox
                    command="sudo apt update && sudo apt install python3.12 python3.12-venv"
                    title="Install Python 3.12"
                    description=""
                  />
                </div>

                <div className="space-y-2">
                  <div className="text-sm font-semibold text-green-900 dark:text-green-100">macOS:</div>
                  <CommandBox
                    command="brew install python@3.12"
                    title="Install using Homebrew"
                    description=""
                  />
                </div>

                <div className="space-y-2">
                  <div className="text-sm font-semibold text-green-900 dark:text-green-100">Windows (WSL):</div>
                  <CommandBox
                    command="sudo apt update && sudo apt install python3.12 python3.12-venv"
                    title="Install in WSL Ubuntu"
                    description="First ensure WSL is installed with Ubuntu"
                  />
                </div>

                <CommandBox
                  command="python3.12 --version"
                  title="Verify Installation"
                  description="Should output: Python 3.12.x"
                />
              </div>
            </Card>

            <Card className="p-4 border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-950">
              <h5 className="font-semibold text-purple-900 dark:text-purple-100 mb-2">Step 3: Setup 4genthub-hooks Client</h5>
              <div className="space-y-3">
                <p className="text-sm text-purple-800 dark:text-purple-200">
                  Add the 4genthub-hooks client to your project:
                </p>

                <CommandBox
                  command="cd your-project"
                  title="Navigate to your project"
                  description=""
                />

                <CommandBox
                  command="sed -i '/^\\.claude$/d' .gitignore"
                  title="Remove .claude from .gitignore"
                  description="Allow .claude directory in git"
                />

                <CommandBox
                  command="git submodule add git@github.com:phamhung075/4genthub-hooks.git .claude"
                  title="Add 4genthub-hooks as submodule"
                  description=""
                />

                <CommandBox
                  command="cd .claude && git checkout main && cd .."
                  title="Configure submodule"
                  description="Track main branch"
                />

                <div className="bg-purple-100 dark:bg-purple-900 p-3 rounded-lg">
                  <p className="text-sm font-semibold text-purple-900 dark:text-purple-100 mb-2">🎯 Simplified Setup - Run ONE Command:</p>

                  <CommandBox
                    command="python3 .claude/hooks/setup_hooks.py"
                    title="Run Automated Setup"
                    description="Handles all configuration automatically"
                  />

                  <p className="text-xs text-purple-800 dark:text-purple-200 mt-3 mb-2">
                    This setup script automatically:
                  </p>
                  <ul className="text-xs text-purple-700 dark:text-purple-300 space-y-1 ml-4 list-disc list-inside">
                    <li>✅ Creates settings.json from template with correct paths</li>
                    <li>✅ Updates .gitignore to exclude local files</li>
                    <li>✅ Untracks configuration files from git</li>
                    <li>✅ Validates all required hook files</li>
                    <li>✅ Tests hook execution</li>
                  </ul>

                  <p className="text-sm font-semibold text-purple-900 dark:text-purple-100 mt-3 mb-2">Then follow the prompts to:</p>

                  <ol className="text-xs text-purple-700 dark:text-purple-300 space-y-2 ml-4 list-decimal list-inside">
                    <li>
                      <strong>Copy CLAUDE configuration files</strong> (if not present):
                      <div className="ml-4 mt-1">
                        <code className="text-xs bg-purple-200 dark:bg-purple-800 px-1 rounded">
                          cp .claude/copy-to-root-project-rename-to:CLAUDE.md CLAUDE.md
                        </code>
                      </div>
                    </li>
                    <li>
                      <strong>Create API configuration</strong>:
                      <div className="ml-4 mt-1">
                        <code className="text-xs bg-purple-200 dark:bg-purple-800 px-1 rounded">
                          cp .claude/.mcp.json.sample .mcp.json
                        </code>
                      </div>
                    </li>
                    <li>
                      <strong>Configure hook protection</strong> (customize for your project):
                      <div className="ml-4 mt-1 text-xs text-purple-600 dark:text-purple-400">
                        Review and edit the files in .claude/hooks/config/
                      </div>
                    </li>
                  </ol>

                  <p className="text-xs text-purple-800 dark:text-purple-200 mt-3">
                    ⚠️ Don't forget to edit <strong>.mcp.json</strong> and add your API token from Step 1
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-4 border-l-4 border-orange-500 bg-orange-50 dark:bg-orange-950">
              <h5 className="font-semibold text-orange-900 dark:text-orange-100 mb-2">Step 4: Configure & Launch Claude Code</h5>
              <div className="space-y-3">
                <p className="text-sm text-orange-800 dark:text-orange-200 mb-3">
                  Edit <strong>.mcp.json</strong> and replace YOUR_API_TOKEN_HERE with your token:
                </p>
                <div className="bg-orange-100 dark:bg-orange-900 p-2 rounded mb-3">
                  <code className="text-xs font-mono">
                    "Authorization": "Bearer YOUR_ACTUAL_TOKEN_HERE"
                  </code>
                </div>

                <CommandBox
                  command="claude-code ."
                  title="Open in Claude Code"
                  description="Hooks will auto-activate"
                />

                <p className="text-sm text-orange-800 dark:text-orange-200">
                  The system will automatically:
                </p>
                <ul className="list-disc list-inside text-sm text-orange-800 dark:text-orange-200 space-y-1 ml-4">
                  <li>✅ Connect to hosted 4genthub service</li>
                  <li>✅ Load master-orchestrator-agent</li>
                  <li>✅ Enable real-time status tracking</li>
                  <li>✅ Activate all 42+ specialized agents</li>
                </ul>

                <div className="bg-orange-100 dark:bg-orange-900 p-3 rounded-lg mt-3">
                  <p className="text-sm font-semibold text-orange-900 dark:text-orange-100 mb-1">Expected Status Line:</p>
                  <code className="text-xs bg-orange-200 dark:bg-orange-800 px-2 py-1 rounded">
                    🎯 Active: master-orchestrator-agent | 🔗 MCP: ✅ Connected | 🌿 main
                  </code>
                </div>
              </div>
            </Card>
          </div>
        </div>

        <div>
          <h4 className="text-lg font-semibold mb-3">Verification</h4>
          <div className="space-y-3">
            <CommandBox
              command='curl -H "Authorization: Bearer YOUR_API_TOKEN" https://api.4genthub.com/mcp/health'
              title="Test Connection"
              description='Should return: {"status": "healthy"}'
            />

            <div className="bg-green-50 dark:bg-green-950 p-4 rounded-lg border border-green-200 dark:border-green-800">
              <h5 className="font-semibold text-green-900 dark:text-green-100 mb-2">Test the Integration:</h5>
              <div className="text-sm text-green-800 dark:text-green-200 space-y-2">
                <p>In Claude Code, try: <strong>"Create a simple hello world function"</strong></p>
                <p className="text-xs">Expected: Auto-delegation to coding-agent with MCP task tracking</p>
              </div>
            </div>

            <div className="bg-blue-50 dark:bg-blue-950 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
              <h5 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Service URLs:</h5>
              <div className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <div>• <strong>API Endpoint:</strong> https://api.4genthub.com</div>
                <div>• <strong>Web Dashboard:</strong> https://www.4genthub.com</div>
                <div>• <strong>Documentation:</strong> https://docs.4genthub.com</div>
                <div>• <strong>Support:</strong> https://discord.gg/4genthub</div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-red-50 dark:bg-red-950 p-4 rounded-lg border border-red-200 dark:border-red-800 mb-6">
          <h4 className="font-semibold text-red-900 dark:text-red-100 mb-2">
            ⚠️ Configuration Validation
          </h4>
          <p className="text-sm text-red-800 dark:text-red-200 mb-2">
            If you see "CLAUDE CODE CONFIGURATION ERROR" when starting:
          </p>
          <ul className="text-xs text-red-700 dark:text-red-300 space-y-1 ml-4 list-disc list-inside">
            <li>The error message shows EXACTLY which files are missing</li>
            <li>Follow the provided fix commands to resolve</li>
            <li>Run <code className="bg-red-200 dark:bg-red-800 px-1 rounded">python3 .claude/hooks/setup_hooks.py</code> again if needed</li>
            <li>All 5 required files must exist: settings.json, .mcp.json, CLAUDE.md, and both hook config files</li>
          </ul>
        </div>

        <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-lg border border-amber-200 dark:border-amber-800">
          <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-2 flex items-center">
            <Zap className="h-4 w-4 mr-2" />
            Why Hosted Service?
          </h4>
          <div className="grid md:grid-cols-2 gap-4 mt-3">
            <ul className="text-sm text-amber-800 dark:text-amber-200 space-y-1">
              <li>✅ No server installation or maintenance</li>
              <li>✅ Enterprise security (SOC2 compliant)</li>
              <li>✅ 99.9% uptime guarantee</li>
              <li>✅ Automatic scaling</li>
            </ul>
            <ul className="text-sm text-amber-800 dark:text-amber-200 space-y-1">
              <li>✅ 42+ specialized agents ready instantly</li>
              <li>✅ Real-time task management</li>
              <li>✅ Zero infrastructure required</li>
              <li>✅ Professional support included</li>
            </ul>
          </div>
        </div>
      </div>
    ),
    isExpanded: expandedSections['getting-started'],
    onToggle: () => toggleSection('getting-started')
  };

  return sectionData;
};

export default GettingStartedGuide;