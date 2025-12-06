import { useEffect, useState } from 'react';
import { marketApi, Opportunity } from '@/lib/api';

export function useOpportunities(refreshInterval: number = 5000) {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOpportunities = async () => {
    try {
      setError(null);
      const data = await marketApi.getOpportunities();
      setOpportunities(data.opportunities || []);
      setIsLoading(false);
    } catch (err: any) {
      setError(err?.message || 'Failed to load opportunities');
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadOpportunities();
    const interval = setInterval(loadOpportunities, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  return {
    opportunities,
    isLoading,
    error,
    refetch: loadOpportunities
  };
}

