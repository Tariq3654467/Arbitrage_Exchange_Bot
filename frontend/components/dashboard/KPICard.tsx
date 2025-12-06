'use client';

import { ReactNode } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    isPositive: boolean;
    label?: string;
  };
  icon?: ReactNode;
  iconColor?: string;
  isLoading?: boolean;
}

export function KPICard({
  title,
  value,
  change,
  icon,
  iconColor = 'text-[#4ade80]',
  isLoading = false
}: KPICardProps) {
  if (isLoading) {
    return (
      <div className="card-premium rounded-card p-5 animate-pulse">
        <div className="h-4 bg-[#1e293b] rounded w-24 mb-3"></div>
        <div className="h-8 bg-[#1e293b] rounded w-32 mb-2"></div>
        <div className="h-3 bg-[#1e293b] rounded w-20"></div>
      </div>
    );
  }

  return (
    <div className="card-premium rounded-card p-5 relative overflow-hidden group hover:shadow-card transition-all duration-200">
      {/* Background gradient accent */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-[#4ade80]/10 to-[#38bdf8]/10 rounded-full blur-2xl -mr-16 -mt-16"></div>
      
      {/* Icon */}
      {icon && (
        <div className={`absolute top-4 right-4 ${iconColor} opacity-20 group-hover:opacity-30 transition-opacity`}>
          {icon}
        </div>
      )}

      {/* Content */}
      <div className="relative">
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
          {title}
        </div>
        <div className="text-2xl font-bold text-white mb-1">
          {value}
        </div>
        {change && (
          <div className={`flex items-center gap-1 text-sm font-semibold ${
            change.isPositive ? 'text-[#4ade80]' : 'text-[#ef4444]'
          }`}>
            {change.isPositive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            <span>
              {change.isPositive ? '+' : ''}{change.value.toFixed(2)}%
            </span>
            {change.label && (
              <span className="text-gray-500 ml-1">{change.label}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

