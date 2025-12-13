import { useEffect, useState } from 'react';
import { botApi, BotStatus } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

// For WebSocket, determine the URL based on the current location
// If accessing remotely, use the same host as the current page
const getWsBase = () => {
  if (typeof window === 'undefined') {
    // Server-side: use Docker hostname
    return (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
  }
  
  // Client-side: use the same host as the current page, but port 8000 for WebSocket
  // This works for both localhost and remote servers
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  return `${protocol}//${host}:8000`;
};

const wsBase = getWsBase();

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

