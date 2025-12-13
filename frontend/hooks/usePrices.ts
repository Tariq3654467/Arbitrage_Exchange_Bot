import { useEffect, useState } from 'react';
import { marketApi } from '@/lib/api';

interface PriceData {
  [symbol: string]: {
    [exchange: string]: {
      bid: number;
      ask: number;
      mid: number;
      spread: number;
      timestamp: string;
    };
  };
}

export function usePrices(showAllPairs: boolean = false, refreshInterval: number = 2000) {
  const [prices, setPrices] = useState<PriceData>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPrices = async () => {
    try {
      setError(null);
      const data = await marketApi.getPrices(showAllPairs);
      
      // Check if response has an error
      if (data && 'error' in data) {
        setError(data.error);
        setPrices(data.prices || {});
      } else {
        setPrices(data || {});
      }
      setIsLoading(false);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.error || err?.message || 'Failed to load prices';
      setError(errorMessage);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPrices();
    const interval = setInterval(loadPrices, refreshInterval);
    return () => clearInterval(interval);
  }, [showAllPairs, refreshInterval]);

  return {
    prices,
    isLoading,
    error,
    refetch: loadPrices
  };
}

