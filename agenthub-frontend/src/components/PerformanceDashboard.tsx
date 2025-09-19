import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Alert, AlertDescription } from './ui/alert';
import { 
  Activity, 
  Database, 
  Layers, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  RefreshCw,
  Zap,
  Clock,
  Users
} from 'lucide-react';
import { api } from '../api';
import logger from '../utils/logger';

// Types for performance data
interface PerformanceMetrics {
  timestamp: string;
  system_health: 'healthy' | 'degraded' | 'critical';
  performance_score: number;
  metrics: {
    connections: {
      sqlite?: {
        type: string;
        status: string;
        pool_size: number;
        connections_created: number;
        avg_wait_time: number;
        hit_rate: number;
      };
      supabase?: {
        type: string;
        status: string;
        pool_size: number;
        checked_out: number;
        overflow: number;
      };
    };
    caching: {
      [cacheName: string]: {
        hit_rate: number;
        size: number;
        max_size: number;
        hits: number;
        misses: number;
        evictions: number;
        status?: string;
      };
    };
    server_health: {
      auth_enabled: boolean;
      database_configured: boolean;
      active_connections: number;
      uptime_seconds: number;
      status: string;
    };
  };
  details?: {
    cache_distribution: { [key: string]: number };
    connection_efficiency: {
      sqlite_avg_wait_ms: number;
      total_connections_created: number;
    };
    performance_recommendations: string[];
  };
}

interface PerformanceAlert {
  type: 'warning' | 'error' | 'info';
  metric: string;
  current_value: number;
  threshold: number;
  message: string;
  cache_name?: string;
}

interface AlertsResponse {
  timestamp: string;
  active_alerts: PerformanceAlert[];
  thresholds: Record<string, number>;
  alert_count: number;
}

const PerformanceDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [alerts, setAlerts] = useState<AlertsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchMetrics = useCallback(async () => {
    try {
      const [metricsResponse, alertsResponse] = await Promise.all([
        api.get('/api/v1/performance/metrics/overview?include_details=true'),
        api.get('/api/v1/performance/metrics/alerts')
      ]);
      
      setMetrics(metricsResponse.data);
      setAlerts(alertsResponse.data);
      setLastUpdated(new Date());
    } catch (error) {
      logger.error('Failed to fetch performance metrics', { error, component: 'PerformanceDashboard' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchMetrics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [autoRefresh, fetchMetrics]);

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getHealthColor = (health: string): string => {
    switch (health) {
      case 'healthy': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      case 'critical': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'degraded': return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'critical': return <AlertTriangle className="h-5 w-5 text-red-600" />;
      default: return <Activity className="h-5 w-5 text-gray-600" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading performance metrics...</span>
      </div>
    );
  }

  if (!metrics) {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Failed to load performance metrics. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Performance Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time system performance and monitoring
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchMetrics}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto-refresh {autoRefresh ? 'ON' : 'OFF'}
          </Button>
        </div>
      </div>

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            {getHealthIcon(metrics.system_health)}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <span className={getHealthColor(metrics.system_health)}>
                {metrics.system_health.toUpperCase()}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Performance Score</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.performance_score.toFixed(1)}</div>
            <div className="text-xs text-muted-foreground">out of 100</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Connections</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.metrics.server_health.active_connections}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatUptime(metrics.metrics.server_health.uptime_seconds)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Section */}
      {alerts && alerts.active_alerts.length > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
              Active Alerts ({alerts.active_alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts.active_alerts.map((alert, index) => (
                <Alert key={index} className="border-yellow-200">
                  <AlertDescription>{alert.message}</AlertDescription>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connection Pool Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Database className="h-5 w-5 mr-2" />
              Connection Pools
            </CardTitle>
            <CardDescription>Database connection pool status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* SQLite Pool */}
              {metrics.metrics.connections.sqlite && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">SQLite Pool</h4>
                    <Badge variant={metrics.metrics.connections.sqlite.status === 'active' ? 'default' : 'secondary'}>
                      {metrics.metrics.connections.sqlite.status}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Pool Size:</span>
                      <div className="font-medium">{metrics.metrics.connections.sqlite.pool_size}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Hit Rate:</span>
                      <div className="font-medium">{(metrics.metrics.connections.sqlite.hit_rate * 100).toFixed(1)}%</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Created:</span>
                      <div className="font-medium">{metrics.metrics.connections.sqlite.connections_created}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Avg Wait:</span>
                      <div className="font-medium">{(metrics.metrics.connections.sqlite.avg_wait_time * 1000).toFixed(1)}ms</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Supabase Pool */}
              {metrics.metrics.connections.supabase && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">PostgreSQL Pool</h4>
                    <Badge variant={metrics.metrics.connections.supabase.status === 'active' ? 'default' : 'secondary'}>
                      {metrics.metrics.connections.supabase.status}
                    </Badge>
                  </div>
                  {metrics.metrics.connections.supabase.status === 'active' && (
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Pool Size:</span>
                        <div className="font-medium">{metrics.metrics.connections.supabase.pool_size}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Checked Out:</span>
                        <div className="font-medium">{metrics.metrics.connections.supabase.checked_out}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Overflow:</span>
                        <div className="font-medium">{metrics.metrics.connections.supabase.overflow}</div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Cache Metrics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Layers className="h-5 w-5 mr-2" />
              Cache Performance
            </CardTitle>
            <CardDescription>Cache hit rates and utilization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(metrics.metrics.caching).map(([cacheName, cacheData]) => {
                if (typeof cacheData !== 'object' || !cacheData.hit_rate) return null;
                
                return (
                  <div key={cacheName} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium capitalize">{cacheName.replace('_', ' ')}</h4>
                      <Badge variant={cacheData.hit_rate > 0.8 ? 'default' : cacheData.hit_rate > 0.6 ? 'secondary' : 'destructive'}>
                        {(cacheData.hit_rate * 100).toFixed(1)}% hit rate
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Size:</span>
                        <div className="font-medium">{cacheData.size} / {cacheData.max_size}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Hits:</span>
                        <div className="font-medium">{cacheData.hits.toLocaleString()}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Misses:</span>
                        <div className="font-medium">{cacheData.misses.toLocaleString()}</div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Evictions:</span>
                        <div className="font-medium">{cacheData.evictions}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Recommendations */}
      {metrics.details?.performance_recommendations && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Zap className="h-5 w-5 mr-2" />
              Performance Recommendations
            </CardTitle>
            <CardDescription>AI-generated optimization suggestions</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {metrics.details.performance_recommendations.map((recommendation, index) => (
                <li key={index} className="flex items-start">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0" />
                  <span>{recommendation}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        Last updated: {lastUpdated.toLocaleTimeString()}
        {autoRefresh && " • Auto-refreshing every 30 seconds"}
      </div>
    </div>
  );
};

export default PerformanceDashboard;