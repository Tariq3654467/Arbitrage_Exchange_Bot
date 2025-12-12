import { useEffect, useState } from 'react';
import { botApi, BotStatus } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

// For WebSocket, use localhost since it can't be proxied through Next.js
// The backend is exposed on localhost:8000 from the host
const wsBase = typeof window !== 'undefined'
  ? 'ws://localhost:8000'  // Client-side: use localhost (backend is exposed on host)
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');  // Server-side: use Docker hostname

export function useBotStatus() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isConnected, lastMessage } = useWebSocket(`${wsBase}/ws`);

  // Initial load
  useEffect(() => {
    loadStatus();
  }, []);

  // WebSocket updates
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'status_update' && lastMessage.data) {
      setStatus(lastMessage.data as BotStatus);
    } else if (lastMessage.type === 'bot_status') {
      if (lastMessage.data) {
        setStatus(lastMessage.data as BotStatus);
      }
    }
  }, [lastMessage]);

  const loadStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await botApi.getStatus();
      setStatus(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load bot status');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    status,
    isLoading,
    error,
    isConnected,
    refetch: loadStatus
  };
}

