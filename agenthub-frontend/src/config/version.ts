/**
 * Version configuration for agenthub Frontend
 * Automatically loads version from package.json
 */

// Import version from package.json
import packageJson from '../../package.json';

// Frontend version - loaded from package.json
export const DEFAULT_VERSION = packageJson.version || "0.0.0";

// Version metadata
export const VERSION_INFO = {
  frontend: DEFAULT_VERSION,
  name: "agenthub Frontend",
  codename: "Vision UI",
  releaseDate: "2025-09-10"
};

// Format version display
export const formatVersionDisplay = (frontend: string, backend?: string): string => {
  if (backend) {
    return `v${frontend} - v${backend}`;
  }
  return `v${frontend} - Backend not connected`;
};