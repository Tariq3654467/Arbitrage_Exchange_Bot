interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ 
  className = '', 
  variant = 'rectangular',
  width,
  height
}: SkeletonProps) {
  const baseStyles = 'animate-pulse bg-slate-800';
  
  const variantStyles = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg'
  };
  
  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;
  
  return (
    <div 
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      style={style}
    />
  );
}

// Pre-built skeleton components
export function SkeletonCard() {
  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4 md:p-5">
      <Skeleton variant="text" width="60%" height={20} className="mb-3" />
      <Skeleton variant="text" width="40%" height={16} className="mb-4" />
      <Skeleton variant="rectangular" width="100%" height={100} />
    </div>
  );
}

export function SkeletonMetric() {
  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4">
      <Skeleton variant="text" width="50%" height={14} className="mb-2" />
      <Skeleton variant="text" width="70%" height={24} className="mb-1" />
      <Skeleton variant="text" width="40%" height={12} />
    </div>
  );
}

