# Logger Environment Variables Configuration

## Overview

The logger system in `agenthub-frontend` now supports full configuration via environment variables. This allows for dynamic configuration without code changes and different settings per environment.

## Required Environment Variables for .env.dev

Add the following environment variables to your `.env.dev` file:

```bash
# Logger Configuration
# Enable/disable logging entirely
REACT_APP_LOG_ENABLED=true

# Log level: debug, info, warn, error, critical
REACT_APP_LOG_LEVEL=debug

# Display options
REACT_APP_LOG_SHOW_TIMESTAMP=true
REACT_APP_LOG_SHOW_LEVEL=true
REACT_APP_LOG_SHOW_FILE_PATH=true
REACT_APP_LOG_COLORIZE=true

# Output destinations
REACT_APP_LOG_TO_CONSOLE=true
REACT_APP_LOG_TO_LOCALSTORAGE=true
REACT_APP_LOG_TO_REMOTE=false

# Storage and batching configuration
REACT_APP_LOG_MAX_STORAGE_SIZE=5242880  # 5MB in bytes
REACT_APP_LOG_BATCH_SIZE=10
REACT_APP_LOG_BATCH_INTERVAL=5000       # 5 seconds in milliseconds

# Remote logging endpoint (optional)
REACT_APP_LOG_REMOTE_ENDPOINT=http://localhost:8000/api/logs/frontend
```

## Environment Variable Details

### Core Settings

- **`REACT_APP_LOG_ENABLED`**: Master switch for logging
  - Values: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` (case-insensitive)
  - Default: `true`

- **`REACT_APP_LOG_LEVEL`**: Minimum log level to display
  - Values: `debug`, `info`, `warn`, `error`, `critical`
  - Default: `info`

### Display Options

- **`REACT_APP_LOG_SHOW_TIMESTAMP`**: Show timestamp in log messages
  - Values: `true`/`false`
  - Default: `true`

- **`REACT_APP_LOG_SHOW_LEVEL`**: Show log level in messages
  - Values: `true`/`false`
  - Default: `true`

- **`REACT_APP_LOG_SHOW_FILE_PATH`**: Show file path in log messages
  - Values: `true`/`false`
  - Default: `false`

- **`REACT_APP_LOG_COLORIZE`**: Use colors in console output
  - Values: `true`/`false`
  - Default: `true`

### Output Destinations

- **`REACT_APP_LOG_TO_CONSOLE`**: Log to browser console
  - Values: `true`/`false`
  - Default: `true`

- **`REACT_APP_LOG_TO_LOCALSTORAGE`**: Store logs in localStorage
  - Values: `true`/`false`
  - Default: `false`

- **`REACT_APP_LOG_TO_REMOTE`**: Send logs to remote endpoint
  - Values: `true`/`false`
  - Default: `false`

### Storage and Performance

- **`REACT_APP_LOG_MAX_STORAGE_SIZE`**: Maximum storage size in bytes
  - Values: Any positive integer
  - Default: `5242880` (5MB)

- **`REACT_APP_LOG_BATCH_SIZE`**: Number of logs to batch before sending
  - Values: Any positive integer
  - Default: `10`

- **`REACT_APP_LOG_BATCH_INTERVAL`**: Batch interval in milliseconds
  - Values: Any positive integer
  - Default: `5000` (5 seconds)

### Remote Logging

- **`REACT_APP_LOG_REMOTE_ENDPOINT`**: URL for remote log endpoint
  - Values: Any valid URL
  - Default: `http://localhost:8000/api/logs/frontend`

## Environment-Specific Presets

The logger configuration includes presets for different environments:

### Development (recommended for .env.dev)
```bash
REACT_APP_LOG_ENABLED=true
REACT_APP_LOG_LEVEL=debug
REACT_APP_LOG_SHOW_TIMESTAMP=true
REACT_APP_LOG_SHOW_LEVEL=true
REACT_APP_LOG_SHOW_FILE_PATH=true
REACT_APP_LOG_COLORIZE=true
REACT_APP_LOG_TO_CONSOLE=true
REACT_APP_LOG_TO_LOCALSTORAGE=true
REACT_APP_LOG_TO_REMOTE=false
REACT_APP_LOG_MAX_STORAGE_SIZE=5242880
REACT_APP_LOG_BATCH_SIZE=10
REACT_APP_LOG_BATCH_INTERVAL=5000
```

### Staging
```bash
REACT_APP_LOG_ENABLED=true
REACT_APP_LOG_LEVEL=info
REACT_APP_LOG_SHOW_TIMESTAMP=true
REACT_APP_LOG_SHOW_LEVEL=true
REACT_APP_LOG_SHOW_FILE_PATH=false
REACT_APP_LOG_COLORIZE=false
REACT_APP_LOG_TO_CONSOLE=true
REACT_APP_LOG_TO_LOCALSTORAGE=true
REACT_APP_LOG_TO_REMOTE=true
REACT_APP_LOG_MAX_STORAGE_SIZE=5242880
REACT_APP_LOG_BATCH_SIZE=10
REACT_APP_LOG_BATCH_INTERVAL=5000
```

### Production
```bash
REACT_APP_LOG_ENABLED=true
REACT_APP_LOG_LEVEL=warn
REACT_APP_LOG_SHOW_TIMESTAMP=true
REACT_APP_LOG_SHOW_LEVEL=true
REACT_APP_LOG_SHOW_FILE_PATH=false
REACT_APP_LOG_COLORIZE=false
REACT_APP_LOG_TO_CONSOLE=false
REACT_APP_LOG_TO_LOCALSTORAGE=false
REACT_APP_LOG_TO_REMOTE=true
REACT_APP_LOG_MAX_STORAGE_SIZE=2097152
REACT_APP_LOG_BATCH_SIZE=20
REACT_APP_LOG_BATCH_INTERVAL=10000
```

## Usage Examples

### Disable all logging
```bash
REACT_APP_LOG_ENABLED=false
```

### Only show errors and critical logs
```bash
REACT_APP_LOG_LEVEL=error
```

### Enable localStorage logging for debugging
```bash
REACT_APP_LOG_TO_LOCALSTORAGE=true
```

### Enable remote logging
```bash
REACT_APP_LOG_TO_REMOTE=true
REACT_APP_LOG_REMOTE_ENDPOINT=https://your-logging-server.com/api/logs
```

## Debugging Configuration

The logger includes a debug helper that can be called to see the current configuration:

```typescript
import { debugLoggerConfig } from '../config/logger.config';

// In development, this will log the current config to console
debugLoggerConfig();
```

## Notes

- Environment variables only take effect after restarting the development server
- Changes to `.env.dev` require a restart: `npm start` or `yarn start`
- Boolean values are parsed flexibly: `true`, `1`, `yes`, `on` are all considered true
- Invalid log levels fall back to `info`
- Invalid numbers fall back to the default values
- All environment variables are optional - the system provides sensible defaults