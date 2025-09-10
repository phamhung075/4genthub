import React from 'react';
import { DEFAULT_VERSION } from '../config/version';

interface VersionDisplayProps {
  backendVersion?: string;
  className?: string;
}

const VersionDisplay: React.FC<VersionDisplayProps> = ({ 
  backendVersion,
  className = "" 
}) => {
  return (
    <div 
      className={`fixed bottom-4 right-4 text-xs text-gray-500 dark:text-gray-400 ${className}`}
    >
      <span className="opacity-75">
        v{DEFAULT_VERSION}
        {backendVersion ? ` - v${backendVersion}` : ' - Backend not connected'}
      </span>
    </div>
  );
};

export default VersionDisplay;