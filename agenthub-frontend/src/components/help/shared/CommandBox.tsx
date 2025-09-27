import React, { useState } from 'react';
import { Button } from '../../ui/button';
import { CheckCircle, Copy } from 'lucide-react';

interface CommandBoxProps {
  command: string;
  title?: string;
  description?: string;
}

const CommandBox: React.FC<CommandBoxProps> = ({ command, title, description }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm">
      {title && (
        <div className="text-green-400 mb-2 font-sans font-medium">{title}</div>
      )}
      {description && (
        <div className="text-gray-400 mb-3 font-sans text-xs">{description}</div>
      )}
      <div className="flex items-center justify-between">
        <code className="flex-1">{command}</code>
        <Button
          size="sm"
          variant="ghost"
          className="text-gray-300 hover:text-white ml-2"
          onClick={copyToClipboard}
        >
          {copied ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
};

export default CommandBox;