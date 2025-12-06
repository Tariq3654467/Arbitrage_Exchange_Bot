'use client';

import { useState, useEffect } from 'react';
import { BotStatus, RiskMetrics } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Bell, User, Clock } from 'lucide-react';

interface HeaderProps {
  botStatus: BotStatus | null;
  riskMetrics: RiskMetrics | null;
  wsConnected: boolean;
  onMenuClick: () => void;
  onStart: () => void;
  onStop: () => void;
  onEmergencyStop?: () => void;
  isStarting: boolean;
  isStopping: boolean;
}

export function Header({
  botStatus,
  riskMetrics,
  wsConnected,
  onMenuClick,
  onStart,
  onStop,
  onEmergencyStop,
  isStarting,
  isStopping
}: HeaderProps) {
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  const [mounted, setMounted] = useState(false);

  // Only set time after component mounts (client-side only)
  useEffect(() => {
    setMounted(true);
    setCurrentTime(new Date());
    
    // Update time every second
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const formattedTime = currentTime?.toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }) || '--:--:--';
  const utcTime = currentTime ? currentTime.toUTCString().split(' ')[4] : '--:--';

  return (
    <header className="sticky top-0 z-30 border-b border-[#1e293b] bg-[#0d1117]/95 backdrop-blur-md">
      <div className="mx-auto flex h-16 items-center justify-between px-6">
        {/* Left: Menu + Time */}
        <div className="flex items-center gap-6">
          <button
            onClick={onMenuClick}
            className="lg:hidden rounded-lg p-2 text-gray-400 hover:bg-[#1e293b] hover:text-white transition-colors"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          
          <div className="flex items-center gap-4">
            {mounted && (
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-gray-400" />
                <span className="text-gray-300 font-mono" suppressHydrationWarning>{formattedTime}</span>
                <span className="text-gray-500" suppressHydrationWarning>UTC {utcTime}</span>
              </div>
            )}
          </div>
        </div>

        {/* Center: Bot Status */}
        <div className="hidden items-center gap-4 md:flex">
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-[#4ade80] animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-xs text-gray-400">
              {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          {botStatus?.is_running && (
            <>
              <div className="h-4 w-px bg-[#1e293b]" />
              <Badge 
                variant="success" 
                size="sm"
                className="bg-[#4ade80]/20 text-[#4ade80] border border-[#4ade80]/30"
              >
                Bot Running
              </Badge>
            </>
          )}
        </div>

        {/* Right: Notifications + User + Controls */}
        <div className="flex items-center gap-3">
          {/* Notifications */}
          <button className="relative rounded-lg p-2 text-gray-400 hover:bg-[#1e293b] hover:text-white transition-colors">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-[#ef4444]"></span>
          </button>

          {/* User/Settings */}
          <button className="rounded-lg p-2 text-gray-400 hover:bg-[#1e293b] hover:text-white transition-colors">
            <User className="h-5 w-5" />
          </button>

          {/* Bot Controls */}
          {botStatus?.is_running && onEmergencyStop && (
            <Button
              variant="danger"
              size="sm"
              onClick={onEmergencyStop}
              className="bg-[#ef4444] hover:bg-[#dc2626] border-0 text-white font-semibold"
            >
              🚨 STOP
            </Button>
          )}
          {botStatus?.is_running ? (
            <Button
              variant="danger"
              size="sm"
              onClick={onStop}
              isLoading={isStopping}
              className="bg-[#1e293b] hover:bg-[#334155] border border-[#334155] text-white"
            >
              Stop Bot
            </Button>
          ) : (
            <Button
              variant="success"
              size="sm"
              onClick={onStart}
              isLoading={isStarting}
              className="bg-[#4ade80] hover:bg-[#22c55e] text-[#0d1117] font-semibold"
            >
              Start Bot
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
