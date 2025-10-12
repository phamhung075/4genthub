
To add the debug panel to your app, add this to your main App component:

import { EnvDebugPanel } from './components/debug/EnvDebugPanel';

// Then in your App component JSX:
{process.env.NODE_ENV === 'development' && <EnvDebugPanel />}

This will show a debug panel in the top-right corner with environment variable information.
