/**
 * Frontend logging utility for unified log management
 */

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  loggerId: string;
  data?: any;
}

class FrontendLogger {
  private logQueue: LogEntry[] = [];
  private loggerId: string;
  private maxQueueSize: number = 100;
  private batchSize: number = 10;
  private batchInterval: number = 5000; // 5 seconds

  constructor() {
    // Generate unique logger ID with timestamp
    this.loggerId = `frontend_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    
    try {
      // Start periodic batch sending
      this.startBatchSending();
      
      // Send logs before page unload
      if (typeof window !== 'undefined') {
        window.addEventListener('beforeunload', () => {
          this.flushLogs();
        });
      }
    } catch (error) {
      console.error('Logger initialization failed, using console fallback:', error);
    }
  }

  private createLogEntry(level: string, message: string, data?: any): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      message,
      loggerId: this.loggerId,
      data
    };
  }

  private formatLogMessage(entry: LogEntry): string {
    const dataStr = entry.data ? ` | Data: ${JSON.stringify(entry.data)}` : '';
    return `[${entry.loggerId}] ${entry.timestamp} - ${entry.level} - ${entry.message}${dataStr}`;
  }

  private async sendToBackend(logs: LogEntry[]): Promise<void> {
    try {
      // Try to send to MCP backend first (port 8000)
      const response = await fetch('http://localhost:8000/api/logs/frontend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs,
          loggerId: this.loggerId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      // If backend is not available, gracefully fallback to console
      if (process.env.NODE_ENV === 'development') {
        console.warn('Backend logging unavailable, using console fallback:', error);
      }
      logs.forEach(log => {
        console.log(this.formatLogMessage(log));
      });
    }
  }

  private startBatchSending(): void {
    setInterval(() => {
      if (this.logQueue.length >= this.batchSize) {
        this.flushLogs();
      }
    }, this.batchInterval);
  }

  private flushLogs(): void {
    if (this.logQueue.length === 0) return;

    const logsToSend = [...this.logQueue];
    this.logQueue = [];
    
    // Send to backend (async, don't wait)
    this.sendToBackend(logsToSend).catch(() => {
      // Fallback to console if backend fails
      logsToSend.forEach(log => {
        console.log(this.formatLogMessage(log));
      });
    });
  }

  debug(message: string, data?: any): void {
    const entry = this.createLogEntry('debug', message, data);
    this.logQueue.push(entry);
    
    // Also log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.debug(this.formatLogMessage(entry));
    }
    
    if (this.logQueue.length > this.maxQueueSize) {
      this.logQueue.shift(); // Remove oldest entry
    }
  }

  info(message: string, data?: any): void {
    const entry = this.createLogEntry('info', message, data);
    this.logQueue.push(entry);
    
    if (process.env.NODE_ENV === 'development') {
      console.info(this.formatLogMessage(entry));
    }
    
    if (this.logQueue.length > this.maxQueueSize) {
      this.logQueue.shift();
    }
  }

  warn(message: string, data?: any): void {
    const entry = this.createLogEntry('warn', message, data);
    this.logQueue.push(entry);
    
    console.warn(this.formatLogMessage(entry));
    
    if (this.logQueue.length > this.maxQueueSize) {
      this.logQueue.shift();
    }
  }

  error(message: string, data?: any): void {
    const entry = this.createLogEntry('error', message, data);
    this.logQueue.push(entry);
    
    console.error(this.formatLogMessage(entry));
    
    // Force flush errors immediately
    this.flushLogs();
  }

  // Get logger info for debugging
  getLoggerInfo(): { loggerId: string; queueSize: number } {
    return {
      loggerId: this.loggerId,
      queueSize: this.logQueue.length
    };
  }
}

// Export singleton instance
export const logger = new FrontendLogger();

// Also export the class for testing
export { FrontendLogger };