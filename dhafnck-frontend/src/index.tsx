import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import reportWebVitals from './reportWebVitals';
import './theme/global.scss';

// Initialize logging system safely
try {
  import('./utils/loggerExport').then(({ logger }) => {
    if (typeof (logger as any).info === 'function') {
      (logger as any).info('Frontend application starting', { 
        version: process.env.REACT_APP_VERSION || '1.0.0',
        nodeEnv: process.env.NODE_ENV
      });
    } else {
      console.log('Frontend application starting (console fallback)');
    }
  }).catch(error => {
    console.log('Frontend application starting (logger unavailable)');
  });
} catch (error) {
  console.log('Frontend application starting (basic mode)');
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
