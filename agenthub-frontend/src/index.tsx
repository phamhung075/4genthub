import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import reportWebVitals from './reportWebVitals';
import './theme/global.scss';
import './styles/notifications.css';

// Initialize extension error filter at the earliest possible point
// This must happen before any other code to catch all extension errors
import { initializeExtensionErrorFilter } from './utils/extensionErrorFilter';
initializeExtensionErrorFilter();

// Initialize logging system safely - only for errors
try {
  import('./utils/loggerExport').then(({ logger }) => {
    // Logger initialized successfully - no need to log startup
  }).catch(error => {
    // Silent fallback - logging system unavailable
  });
} catch (error) {
  // Silent fallback - basic mode
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
