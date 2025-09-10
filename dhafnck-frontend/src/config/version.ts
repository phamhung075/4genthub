/**
 * Version configuration for DhafnckMCP Frontend
 * Update DEFAULT_VERSION when releasing new frontend versions
 */

// Frontend version
export const DEFAULT_VERSION = "0.0.2";

// Version metadata
export const VERSION_INFO = {
  frontend: DEFAULT_VERSION,
  name: "DhafnckMCP Frontend",
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