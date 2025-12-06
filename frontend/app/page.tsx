/* Main Next.js dashboard page - Redirects to new dashboard */
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * This page redirects to the new dashboard at /dashboard
 * The legacy dashboard code has been moved to /app/dashboard/page.tsx
 */
export default function DashboardPage() {
  const router = useRouter();
  
  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);
  
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <div className="text-center">
        <div className="mb-4 text-4xl animate-pulse">🤖</div>
        <div className="text-xl font-semibold text-slate-100">Loading Dashboard...</div>
      </div>
    </div>
  );
}
