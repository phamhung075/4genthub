import { ArrowLeft } from 'lucide-react';
import React, { useState } from 'react';
import {
  DockerSetup,
  GettingStartedGuide,
  HelpSection,
  MCPConfiguration,
  Troubleshooting,
  UsingMCPTools,
  WhatIs4genthub
} from '../components/help';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

export const HelpSetup: React.FC = () => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [searchTerm, setSearchTerm] = useState('');

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionId]: !prev[sectionId]
    }));
  };

  // Create section data from components
  const helpSections = [
    WhatIs4genthub({ expandedSections, toggleSection }),
    GettingStartedGuide({ expandedSections, toggleSection }),
    MCPConfiguration({ expandedSections, toggleSection }),
    UsingMCPTools({ expandedSections, toggleSection }),
    DockerSetup({ expandedSections, toggleSection }),
    Troubleshooting({ expandedSections, toggleSection })
  ];

  const filteredSections = helpSections.filter(section =>
    section.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    section.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const expandAll = () => {
    const allExpanded: Record<string, boolean> = {};
    helpSections.forEach(section => {
      allExpanded[section.id] = true;
    });
    setExpandedSections(allExpanded);
  };

  const collapseAll = () => {
    setExpandedSections({});
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center mb-4">
            <Button
              variant="ghost"
              onClick={() => window.history.back()}
              className="mr-4"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              4genthub Help & Setup Guide
            </h1>
          </div>

          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Complete guide to setting up and using 4genthub MCP platform with 32 specialized AI agents
          </p>

          {/* Search and Controls */}
          <div className="flex flex-col sm:flex-row gap-4 items-center mb-6">
            <div className="flex-1 max-w-md">
              <Input
                type="text"
                placeholder="Search help sections..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={expandAll} size="sm">
                Expand All
              </Button>
              <Button variant="outline" onClick={collapseAll} size="sm">
                Collapse All
              </Button>
            </div>
          </div>
        </div>

        {/* Help Sections */}
        <div className="space-y-6">
          {filteredSections.length > 0 ? (
            filteredSections.map((section) => (
              <HelpSection
                key={section.id}
                id={section.id}
                title={section.title}
                description={section.description}
                icon={section.icon}
                content={section.content}
                isExpanded={section.isExpanded}
                onToggle={section.onToggle}
              />
            ))
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500 dark:text-gray-400">
                No sections found matching "{searchTerm}"
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-800">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <p className="mb-2">
              Need more help? Join our community or check the documentation.
            </p>
            <div className="flex justify-center space-x-6 text-sm">
              <a
                href="https://discord.gg/zmhMpK6N"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 transition-colors"
              >
                Discord Community
              </a>
              <a
                href="https://github.com/phamhung075/4genthub"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 transition-colors"
              >
                GitHub Repository
              </a>
              <a
                href="https://docs.4genthub.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-blue-600 transition-colors"
              >
                Full Documentation
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
