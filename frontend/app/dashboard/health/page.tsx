'use client';

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { systemApi, SystemHealth } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export default function HealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadHealth();
    loadLogs();
    const interval = setInterval(() => {
      loadHealth();
      loadLogs();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadHealth = async () => {
    try {
      const data = await systemApi.getHealth();
      setHealth(data);
    } catch (err) {
      console.error('Error loading health:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      const data = await systemApi.getLogs(undefined, 50);
      setLogs(data || []);
    } catch (err) {
      console.error('Error loading logs:', err);
    }
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-100">System Health</h1>
          <p className="text-sm text-slate-400 mt-1">
            Monitor bot components, databases, and system status
          </p>
        </div>

        {/* Overall Status */}
        {health && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>System Status</CardTitle>
                <Badge
                  variant={
                    health.status === 'healthy' ? 'success' :
                    health.status === 'degraded' ? 'warning' : 'error'
                  }
                >
                  {health.status.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {health.issues && health.issues.length > 0 && (
                <div className="mb-4 p-3 rounded-lg bg-amber-500/20 border border-amber-500/40">
                  <div className="text-sm font-semibold text-amber-200 mb-1">Issues Detected:</div>
                  <ul className="list-disc list-inside text-sm text-amber-100">
                    {health.issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="text-xs text-slate-400">
                Last updated: {new Date(health.timestamp).toLocaleString()}
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Bot Status */}
          <Card>
            <CardHeader>
              <CardTitle>Bot Status</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="py-4 text-center text-slate-400">Loading...</div>
              ) : health ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Running</span>
                    <Badge variant={health.bot.running ? 'success' : 'default'}>
                      {health.bot.running ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Uptime</span>
                    <span className="text-sm font-semibold text-slate-200">
                      {formatUptime(health.bot.uptime_seconds)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Mode</span>
                    <Badge variant={health.bot.paper_trading ? 'warning' : 'error'}>
                      {health.bot.paper_trading ? 'Paper' : 'Live'}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-slate-400">No data</div>
              )}
            </CardContent>
          </Card>

          {/* Exchanges */}
          <Card>
            <CardHeader>
              <CardTitle>Exchanges</CardTitle>
            </CardHeader>
            <CardContent>
              {health ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Connected</span>
                    <span className="text-sm font-semibold text-slate-200">
                      {health.exchanges.connected} / {health.exchanges.total}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 transition-all"
                      style={{
                        width: `${health.exchanges.total > 0 ? (health.exchanges.connected / health.exchanges.total) * 100 : 0}%`
                      }}
                    />
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-slate-400">No data</div>
              )}
            </CardContent>
          </Card>

          {/* Databases */}
          <Card>
            <CardHeader>
              <CardTitle>Databases</CardTitle>
            </CardHeader>
            <CardContent>
              {health ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">PostgreSQL</span>
                    <Badge variant={health.databases.postgres ? 'success' : 'error'}>
                      {health.databases.postgres ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">InfluxDB</span>
                    <Badge variant={health.databases.influxdb ? 'success' : 'error'}>
                      {health.databases.influxdb ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-slate-400">No data</div>
              )}
            </CardContent>
          </Card>

          {/* Components */}
          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>Bot Components</CardTitle>
            </CardHeader>
            <CardContent>
              {health ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50">
                    <span className="text-sm text-slate-400">Price Monitor</span>
                    <Badge variant={health.components.price_monitor ? 'success' : 'error'}>
                      {health.components.price_monitor ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50">
                    <span className="text-sm text-slate-400">Trade Executor</span>
                    <Badge variant={health.components.trade_executor ? 'success' : 'error'}>
                      {health.components.trade_executor ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50">
                    <span className="text-sm text-slate-400">Risk Manager</span>
                    <Badge variant={health.components.risk_manager ? 'success' : 'error'}>
                      {health.components.risk_manager ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50">
                    <span className="text-sm text-slate-400">Portfolio Manager</span>
                    <Badge variant={health.components.portfolio_manager ? 'success' : 'error'}>
                      {health.components.portfolio_manager ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-slate-400">No data</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* System Logs */}
        <Card>
          <CardHeader>
            <CardTitle>Recent System Logs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="py-8 text-center text-slate-400">No logs available</div>
              ) : (
                <div className="space-y-1 font-mono text-xs">
                  {logs.map((log, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded ${
                        log.includes('ERROR') ? 'bg-rose-500/10 text-rose-300' :
                        log.includes('WARNING') ? 'bg-amber-500/10 text-amber-300' :
                        log.includes('INFO') ? 'bg-blue-500/10 text-blue-300' :
                        'bg-slate-800/50 text-slate-300'
                      }`}
                    >
                      {log}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

