import { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Badge({ 
  children, 
  variant = 'default',
  size = 'md',
  className = ''
}: BadgeProps) {
  const baseStyles = 'inline-flex items-center justify-center rounded-full font-medium';
  
  const variantStyles = {
    default: 'bg-[#1e293b] text-gray-300 border border-[#334155]',
    success: 'bg-[#4ade80]/20 text-[#4ade80] border border-[#4ade80]/30',
    warning: 'bg-[#fbbf24]/20 text-[#fbbf24] border border-[#fbbf24]/30',
    error: 'bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/30',
    info: 'bg-[#60a5fa]/20 text-[#60a5fa] border border-[#60a5fa]/30'
  };
  
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm'
  };
  
  return (
    <span className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}>
      {children}
    </span>
  );
}
