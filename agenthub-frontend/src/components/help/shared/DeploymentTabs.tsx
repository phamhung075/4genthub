import React from 'react';
import { Card } from '../../ui/card';

interface DeploymentTabsProps {
  localContent: React.ReactNode;
  cloudContent: React.ReactNode;
  defaultMode?: 'local' | 'cloud';
}

const DeploymentTabs: React.FC<DeploymentTabsProps> = ({
  localContent,
  cloudContent,
  defaultMode = 'cloud'
}) => {
  // Use the prop directly instead of internal state - controlled by parent
  return (
    <div className="mt-4">
      {defaultMode === 'local' ? (
        <div className="animate-in fade-in duration-200">
          {localContent}
        </div>
      ) : (
        <div className="animate-in fade-in duration-200">
          {cloudContent}
        </div>
      )}
    </div>
  );
};

export default DeploymentTabs;
