import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { debugAnimationSupport, getShimmerCSS } from '../utils/animationSupport';
import ShimmerButtonFixed from './ui/ShimmerButtonFixed';
import { webSocketAnimationService } from '../services/WebSocketAnimationService';

const AnimationDiagnostic: React.FC = () => {
  const [diagnostics, setDiagnostics] = useState({
    cssPropertySupport: false,
    framerMotionLoaded: false,
    browserInfo: '',
    errors: [] as string[]
  });

  useEffect(() => {
    const runDiagnostics = () => {
      const results = {
        cssPropertySupport: false,
        framerMotionLoaded: false,
        browserInfo: navigator.userAgent,
        errors: [] as string[]
      };

      // Test CSS @property support
      try {
        // @ts-ignore
        results.cssPropertySupport = CSS.supports('@property', '--test');
      } catch (error) {
        results.errors.push(`CSS @property test failed: ${error}`);
      }

      // Test Framer Motion availability
      try {
        results.framerMotionLoaded = typeof motion !== 'undefined';
      } catch (error) {
        results.errors.push(`Framer Motion test failed: ${error}`);
      }

      setDiagnostics(results);
    };

    runDiagnostics();
  }, []);

  return (
    <div className="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-w-2xl mx-auto my-8">
      <h2 className="text-2xl font-bold mb-4 text-gray-900 dark:text-white">🔍 Animation Diagnostics</h2>

      <div className="space-y-4">
        {/* CSS @property support */}
        <div className={`p-3 rounded-md ${diagnostics.cssPropertySupport ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          <strong>CSS @property Support:</strong> {diagnostics.cssPropertySupport ? '✅ Supported' : '❌ Not Supported'}
        </div>

        {/* Framer Motion */}
        <div className={`p-3 rounded-md ${diagnostics.framerMotionLoaded ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          <strong>Framer Motion:</strong> {diagnostics.framerMotionLoaded ? '✅ Loaded' : '❌ Not Loaded'}
        </div>

        {/* Browser info */}
        <div className="p-3 bg-blue-100 text-blue-800 rounded-md">
          <strong>Browser:</strong> {diagnostics.browserInfo}
        </div>

        {/* Errors */}
        {diagnostics.errors.length > 0 && (
          <div className="p-3 bg-red-100 text-red-800 rounded-md">
            <strong>Errors:</strong>
            <ul className="mt-2 ml-4 list-disc">
              {diagnostics.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Live animation tests */}
        <div className="border-t pt-4">
          <h3 className="text-lg font-semibold mb-3">Live Animation Tests:</h3>

          {/* CSS @property animation test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">CSS @property Shimmer Test:</h4>
            <div
              className="w-24 h-24 mx-auto relative rounded-full overflow-hidden"
              style={{
                background: 'gray',
                padding: '2px'
              }}
            >
              <div className="test-shimmer-bg absolute inset-0" />
              <div className="relative z-10 bg-white dark:bg-gray-800 rounded-full w-full h-full flex items-center justify-center">
                CSS
              </div>
            </div>
          </div>

          {/* Framer Motion test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Framer Motion Test:</h4>
            <motion.div
              className="w-24 h-24 mx-auto bg-blue-500 rounded-full flex items-center justify-center text-white font-bold"
              animate={{
                rotate: [0, 360],
                scale: [1, 1.1, 1]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              Motion
            </motion.div>
          </div>

          {/* Basic CSS animation test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Basic CSS Animation Test:</h4>
            <div
              className="w-24 h-24 mx-auto bg-green-500 rounded-full flex items-center justify-center text-white font-bold"
              style={{
                animation: 'spin 2s linear infinite'
              }}
            >
              CSS
            </div>
          </div>

          {/* Fixed ShimmerButton test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Fixed ShimmerButton Test:</h4>
            <div className="flex justify-center">
              <ShimmerButtonFixed variant="default" size="default" className="mx-2">
                Fixed Shimmer
              </ShimmerButtonFixed>
            </div>
          </div>

          {/* Debug output */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Debug Output:</h4>
            <button
              onClick={() => {
                const info = debugAnimationSupport();
                console.log('Debug info:', info);
              }}
              className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
            >
              Log Animation Debug Info
            </button>
          </div>

          {/* WebSocket Animation Tests */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">WebSocket Animation Tests:</h4>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => {
                  console.log('🧪 Testing task created animation');
                  webSocketAnimationService.triggerTestAnimation('created', 'task');
                }}
                className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 text-sm"
              >
                Test Task Created
              </button>
              <button
                onClick={() => {
                  console.log('🧪 Testing task updated animation');
                  webSocketAnimationService.triggerTestAnimation('updated', 'task');
                }}
                className="px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
              >
                Test Task Updated
              </button>
              <button
                onClick={() => {
                  console.log('🧪 Testing task completed animation');
                  webSocketAnimationService.triggerTestAnimation('completed', 'task');
                }}
                className="px-3 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600 text-sm"
              >
                Test Task Completed
              </button>
              <button
                onClick={() => {
                  console.log('🧪 Testing task deleted animation');
                  webSocketAnimationService.triggerTestAnimation('deleted', 'task');
                }}
                className="px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
              >
                Test Task Deleted
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnimationDiagnostic;