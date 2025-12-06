import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'success';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center rounded-button font-semibold transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50';
  
  const variantStyles = {
    primary: 'bg-[#60a5fa] text-white hover:bg-[#3b82f6] active:bg-[#2563eb] shadow-lg hover:shadow-xl',
    secondary: 'bg-[#1e293b] text-gray-200 hover:bg-[#334155] active:bg-[#475569] border border-[#334155]',
    danger: 'bg-[#ef4444] text-white hover:bg-[#dc2626] active:bg-[#b91c1c] shadow-lg hover:shadow-xl',
    ghost: 'bg-transparent text-gray-300 hover:bg-[#1e293b] active:bg-[#334155]',
    success: 'bg-[#4ade80] text-[#0d1117] hover:bg-[#22c55e] active:bg-[#16a34a] font-bold shadow-lg hover:shadow-xl'
  };
  
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  };
  
  return (
    <button
      className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <svg className="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading...
        </>
      ) : (
        children
      )}
    </button>
  );
}
