'use client';

import { useState, useEffect } from 'react';
import { useBotStatus } from '@/hooks/useBotStatus';
import { riskApi, botApi } from '@/lib/api';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [riskMetrics, setRiskMetrics] = useState<any>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);

  const { status: botStatus, isConnected, refetch: refetchStatus } = useBotStatus();

  // Load risk metrics
  useEffect(() => {
    const loadRiskMetrics = async () => {
      try {
        const risk = await riskApi.getMetrics();
        if (!('error' in risk)) {
          setRiskMetrics(risk);
        }
      } catch (err) {
        console.error('Error loading risk metrics:', err);
      }
    };

    loadRiskMetrics();
    const interval = setInterval(loadRiskMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    if (!botStatus?.paper_trading) {
      const confirmed = window.confirm(
        `🚨 PRODUCTION MODE - LIVE TRADING\n\n` +
        `⚠️ WARNING: You are about to start the bot in LIVE TRADING mode.\n\n` +
        `This will use REAL FUNDS and execute REAL TRADES.\n\n` +
        `Are you absolutely sure you want to proceed?`
      );
      if (!confirmed) return;
    }

    try {
      setIsStarting(true);
      await botApi.start();
      await refetchStatus();
    } catch (err: any) {
      alert(err?.message || 'Failed to start bot');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    try {
      setIsStopping(true);
      await botApi.stop();
      await refetchStatus();
    } catch (err: any) {
      alert(err?.message || 'Failed to stop bot');
    } finally {
      setIsStopping(false);
    }
  };

  const handleEmergencyStop = async () => {
    const confirmed = window.confirm(
      `🚨 EMERGENCY STOP\n\n` +
      `This will IMMEDIATELY halt all trading and cancel all pending orders.\n\n` +
      `This action cannot be undone easily. Are you absolutely sure?`
    );
    if (!confirmed) return;

    try {
      await botApi.emergencyStop();
      await refetchStatus();
      alert('Emergency stop activated! All trading has been halted.');
    } catch (err: any) {
      alert(`Emergency stop failed: ${err?.message || 'Unknown error'}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      
      <div className="lg:pl-64">
        <Header
          botStatus={botStatus}
          riskMetrics={riskMetrics}
          wsConnected={isConnected}
          onMenuClick={() => setSidebarOpen(true)}
          onStart={handleStart}
          onStop={handleStop}
          onEmergencyStop={handleEmergencyStop}
          isStarting={isStarting}
          isStopping={isStopping}
        />

        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
