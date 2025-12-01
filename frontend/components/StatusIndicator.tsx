'use client';

import { BotStatus } from '@/lib/api';

interface StatusIndicatorProps {
  status: BotStatus | null;
}

export default function StatusIndicator({ status }: StatusIndicatorProps) {
  const isRunning = status?.is_running ?? false;
  
  return (
    <div className="flex items-center gap-3">
      <div className={`relative w-3 h-3 rounded-full ${isRunning ? 'bg-green-500 animate-pulse-glow' : 'bg-red-500'}`}>
        {isRunning && (
          <div className="absolute inset-0 rounded-full bg-green-500 animate-ping opacity-75" />
        )}
      </div>
      <span className="font-semibold text-gray-700">
        {isRunning ? 'Running' : 'Stopped'}
      </span>
    </div>
  );
}

