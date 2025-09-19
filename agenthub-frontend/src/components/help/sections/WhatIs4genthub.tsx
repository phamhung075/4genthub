import React from 'react';
import { Button } from '../../ui/button';
import { Card } from '../../ui/card';
import {
  Book,
  GitBranch,
  MessageSquare,
  ExternalLink,
  Zap,
  CheckCircle
} from 'lucide-react';

interface WhatIs4genthubProps {
  expandedSections: Record<string, boolean>;
  toggleSection: (sectionId: string) => void;
}

const WhatIs4genthub: React.FC<WhatIs4genthubProps> = ({ expandedSections, toggleSection }) => {
  const sectionData = {
    id: 'what-is-4genthub',
    title: 'What is 4genthub MCP?',
    description: 'Overview of 4genthub as enterprise MCP platform with community links',
    icon: <Book className="h-6 w-6 text-blue-500" />,
    content: (
      <div className="space-y-6">
        <p className="text-base leading-relaxed">
          4genthub is a revolutionary enterprise MCP (Model Context Protocol) platform that enables seamless
          collaboration between AI agents and developers. It provides a structured way to manage tasks, contexts,
          and agent interactions in software development projects with 42+ specialized agents.
        </p>

        {/* Community Links as Prominent Cards */}
        <div className="grid md:grid-cols-2 gap-4">
          <Card className="p-4 bg-gradient-to-br from-gray-900 to-gray-800 text-white border-gray-700 hover:border-gray-600 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <GitBranch className="h-8 w-8" />
                <div>
                  <h4 className="font-bold text-lg">GitHub Repository</h4>
                  <p className="text-gray-300 text-sm">Open source codebase and contributions</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-white hover:text-gray-200"
                onClick={() => window.open('https://github.com/phamhung075/4genthub', '_blank')}
              >
                <ExternalLink className="h-4 w-4" />
              </Button>
            </div>
          </Card>

          <Card className="p-4 bg-gradient-to-br from-indigo-600 to-purple-700 text-white border-indigo-500 hover:border-indigo-400 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <MessageSquare className="h-8 w-8" />
                <div>
                  <h4 className="font-bold text-lg">Discord Community</h4>
                  <p className="text-indigo-100 text-sm">Join our developer community</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-white hover:text-indigo-100"
                onClick={() => window.open('https://discord.gg/zmhMpK6N', '_blank')}
              >
                <ExternalLink className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        </div>

        {/* Key Features and Benefits */}
        <div className="grid md:grid-cols-2 gap-4 mt-6">
          <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
            <h4 className="font-semibold text-blue-900 dark:text-blue-100 flex items-center mb-2">
              <Zap className="h-4 w-4 mr-2" />
              Key Features
            </h4>
            <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
              <li>• 42+ specialized AI agents</li>
              <li>• Intelligent task management</li>
              <li>• 4-tier context hierarchy</li>
              <li>• Enterprise orchestration</li>
              <li>• Vision System capabilities</li>
            </ul>
          </Card>
          <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
            <h4 className="font-semibold text-green-900 dark:text-green-100 flex items-center mb-2">
              <CheckCircle className="h-4 w-4 mr-2" />
              Benefits
            </h4>
            <ul className="text-sm text-green-800 dark:text-green-200 space-y-1">
              <li>• Accelerated development</li>
              <li>• Improved code quality</li>
              <li>• Parallel agent coordination</li>
              <li>• Enhanced documentation</li>
              <li>• Real-time collaboration</li>
            </ul>
          </Card>
        </div>
      </div>
    ),
    isExpanded: expandedSections['what-is-4genthub'],
    onToggle: () => toggleSection('what-is-4genthub')
  };

  return sectionData;
};

export default WhatIs4genthub;