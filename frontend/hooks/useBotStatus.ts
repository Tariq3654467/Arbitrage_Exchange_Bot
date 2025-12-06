import { useEffect, useState } from 'react';
import { botApi, BotStatus } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const wsBase = apiBase.replace(/^http/, 'ws');

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

