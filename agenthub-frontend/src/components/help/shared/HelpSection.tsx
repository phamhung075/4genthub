import React from 'react';
import { Button } from '../../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface HelpSectionProps {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  content: React.ReactNode;
  isExpanded?: boolean;
  onToggle?: () => void;
}

const HelpSection: React.FC<HelpSectionProps> = ({
  title,
  description,
  icon,
  content,
  isExpanded = false,
  onToggle
}) => (
  <Card className="mb-6">
    <CardHeader className="cursor-pointer" onClick={onToggle}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {icon}
          <div>
            <CardTitle className="text-xl">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
        <Button variant="ghost" size="sm">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </Button>
      </div>
    </CardHeader>
    {isExpanded && (
      <CardContent>
        {content}
      </CardContent>
    )}
  </Card>
);

export default HelpSection;