/**
 * Validation Statistics Exporter
 * Provides utilities to export and analyze validation statistics
 */

import { ValidationStats } from './responseValidator';
import { WSValidationStats } from './websocketValidator';
import logger from './logger';

export interface ValidationReport {
  timestamp: string;
  apiValidation: ReturnType<typeof ValidationStats.getStats>;
  websocketValidation: ReturnType<typeof WSValidationStats.getStats>;
  summary: {
    totalValidations: number;
    totalFailures: number;
    overallFailureRate: string;
    criticalIssues: string[];
  };
}

/**
 * Generate comprehensive validation report
 */
export function generateValidationReport(): ValidationReport {
  const apiStats = ValidationStats.getStats();
  const wsStats = WSValidationStats.getStats();

  const totalValidations = apiStats.totalValidations + wsStats.totalMessages;
  const totalFailures = apiStats.failedValidations + wsStats.failedMessages;
  const overallFailureRate = totalValidations > 0
    ? (totalFailures / totalValidations * 100).toFixed(2) + '%'
    : '0%';

  // Identify critical issues (fields failing most often)
  const criticalIssues: string[] = [];

  // From API validation
  Object.entries(apiStats.errorsByField).forEach(([field, count]) => {
    if (typeof count === 'number' && count >= 3) {
      criticalIssues.push(`API: ${field} failed ${count} times`);
    }
  });

  // From WebSocket validation
  Object.entries(wsStats.errorsByType).forEach(([type, count]) => {
    if (typeof count === 'number' && count >= 3) {
      criticalIssues.push(`WS: ${type} messages failed ${count} times`);
    }
  });

  return {
    timestamp: new Date().toISOString(),
    apiValidation: apiStats,
    websocketValidation: wsStats,
    summary: {
      totalValidations,
      totalFailures,
      overallFailureRate,
      criticalIssues
    }
  };
}

/**
 * Export validation report as JSON
 */
export function exportValidationReportJSON(): string {
  const report = generateValidationReport();
  return JSON.stringify(report, null, 2);
}

/**
 * Export validation report as Markdown
 */
export function exportValidationReportMarkdown(): string {
  const report = generateValidationReport();

  let markdown = `# Response Validation Report\n\n`;
  markdown += `**Generated:** ${report.timestamp}\n\n`;

  markdown += `## Summary\n\n`;
  markdown += `- **Total Validations:** ${report.summary.totalValidations}\n`;
  markdown += `- **Total Failures:** ${report.summary.totalFailures}\n`;
  markdown += `- **Overall Failure Rate:** ${report.summary.overallFailureRate}\n\n`;

  if (report.summary.criticalIssues.length > 0) {
    markdown += `### Critical Issues\n\n`;
    report.summary.criticalIssues.forEach(issue => {
      markdown += `- ⚠️ ${issue}\n`;
    });
    markdown += `\n`;
  }

  markdown += `## API Response Validation\n\n`;
  markdown += `- **Total Validations:** ${report.apiValidation.totalValidations}\n`;
  markdown += `- **Failed Validations:** ${report.apiValidation.failedValidations}\n`;
  markdown += `- **Failure Rate:** ${report.apiValidation.failureRate}\n`;
  markdown += `- **Total Warnings:** ${report.apiValidation.warningCount}\n\n`;

  if (Object.keys(report.apiValidation.errorsByField).length > 0) {
    markdown += `### Errors by Field\n\n`;
    markdown += `| Field | Error Count |\n`;
    markdown += `|-------|-------------|\n`;
    Object.entries(report.apiValidation.errorsByField).forEach(([field, count]) => {
      markdown += `| ${field} | ${count} |\n`;
    });
    markdown += `\n`;
  }

  if (Object.keys(report.apiValidation.errorsByEndpoint).length > 0) {
    markdown += `### Errors by Endpoint\n\n`;
    markdown += `| Endpoint | Error Count |\n`;
    markdown += `|----------|-------------|\n`;
    Object.entries(report.apiValidation.errorsByEndpoint).forEach(([endpoint, count]) => {
      markdown += `| ${endpoint} | ${count} |\n`;
    });
    markdown += `\n`;
  }

  markdown += `## WebSocket Message Validation\n\n`;
  markdown += `- **Total Messages:** ${report.websocketValidation.totalMessages}\n`;
  markdown += `- **Failed Messages:** ${report.websocketValidation.failedMessages}\n`;
  markdown += `- **Failure Rate:** ${report.websocketValidation.failureRate}\n`;
  markdown += `- **Total Warnings:** ${report.websocketValidation.warningCount}\n\n`;

  if (Object.keys(report.websocketValidation.messagesByType).length > 0) {
    markdown += `### Messages by Type\n\n`;
    markdown += `| Message Type | Count |\n`;
    markdown += `|--------------|-------|\n`;
    Object.entries(report.websocketValidation.messagesByType).forEach(([type, count]) => {
      markdown += `| ${type} | ${count} |\n`;
    });
    markdown += `\n`;
  }

  if (Object.keys(report.websocketValidation.errorsByType).length > 0) {
    markdown += `### Errors by Message Type\n\n`;
    markdown += `| Message Type | Error Count |\n`;
    markdown += `|--------------|-------------|\n`;
    Object.entries(report.websocketValidation.errorsByType).forEach(([type, count]) => {
      markdown += `| ${type} | ${count} |\n`;
    });
    markdown += `\n`;
  }

  return markdown;
}

/**
 * Download validation report as file
 */
export function downloadValidationReport(format: 'json' | 'markdown' = 'markdown') {
  const report = format === 'json' ? exportValidationReportJSON() : exportValidationReportMarkdown();
  const filename = `validation-report-${new Date().toISOString().split('T')[0]}.${format === 'json' ? 'json' : 'md'}`;
  const blob = new Blob([report], { type: format === 'json' ? 'application/json' : 'text/markdown' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();

  URL.revokeObjectURL(url);

  logger.info(`📥 [Validation Report] Downloaded as ${filename}`);
}

/**
 * Log validation report to console
 */
export function logValidationReport() {
  const report = generateValidationReport();
  logger.info('📊 [Validation Report] Full Report', report);
  console.log('\n' + exportValidationReportMarkdown());
}

/**
 * Reset all validation statistics
 */
export function resetValidationStats() {
  ValidationStats.reset();
  WSValidationStats.reset();
  logger.info('🔄 [Validation Stats] Reset all statistics');
}

// Make utilities available globally in development
if (import.meta.env.DEV) {
  (window as any).__validationUtils = {
    getReport: generateValidationReport,
    exportJSON: exportValidationReportJSON,
    exportMarkdown: exportValidationReportMarkdown,
    download: downloadValidationReport,
    log: logValidationReport,
    reset: resetValidationStats
  };

  logger.info('🔧 [Validation Utils] Global utilities available:', {
    usage: 'window.__validationUtils',
    methods: ['getReport()', 'exportJSON()', 'exportMarkdown()', 'download(format)', 'log()', 'reset()']
  });
}
