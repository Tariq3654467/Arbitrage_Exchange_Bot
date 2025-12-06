'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon?: string;
  isLoading?: boolean;
}

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  isLoading = false
}: MetricCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton variant="text" width="60%" height={14} />
        </CardHeader>
        <CardContent>
          <Skeleton variant="text" width="40%" height={24} className="mb-2" />
          {subtitle && <Skeleton variant="text" width="70%" height={12} />}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated" className="relative overflow-hidden">
      {icon && (
        <div className="absolute right-4 top-4 text-4xl opacity-10">
          {icon}
        </div>
      )}
      <CardHeader>
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-blue-300">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold text-blue-100 md:text-3xl">
            {value}
          </div>
          {trend && (
            <div className={`text-sm font-semibold ${
              trend.isPositive ? 'text-emerald-400' : 'text-rose-400'
            }`}>
              {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value).toFixed(2)}%
            </div>
          )}
        </div>
        {subtitle && (
          <p className="mt-2 text-xs text-blue-400">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

