'use client';

import { usePathname, useRouter } from 'next/navigation';
import { 
  LayoutDashboard, 
  TrendingUp, 
  FileText, 
  Wallet, 
  BarChart3,
  Settings
} from 'lucide-react';

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: string;
}

const navItems: NavItem[] = [
  { id: 'overview', label: 'Dashboard', icon: <LayoutDashboard className="h-5 w-5" />, href: '/dashboard' },
  { id: 'opportunities', label: 'Opportunities', icon: <TrendingUp className="h-5 w-5" />, href: '/dashboard/opportunities' },
  { id: 'trades', label: 'Trade History', icon: <FileText className="h-5 w-5" />, href: '/dashboard/trades' },
  { id: 'market', label: 'Market Data', icon: <BarChart3 className="h-5 w-5" />, href: '/dashboard/market' },
  { id: 'balances', label: 'Portfolio', icon: <Wallet className="h-5 w-5" />, href: '/dashboard/balances' },
  { id: 'config', label: 'Settings', icon: <Settings className="h-5 w-5" />, href: '/dashboard/config' },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  
  const handleNav = (href: string) => {
    if (href.startsWith('/dashboard')) {
      router.push(href);
    }
    onClose();
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-50 h-full w-64 transform bg-[#0d1117] backdrop-blur-md transition-transform duration-300 lg:translate-x-0 border-r border-[#1e293b] ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex items-center gap-3 border-b border-[#1e293b] p-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-[#4ade80] to-[#38bdf8]">
              <span className="text-xl font-bold text-[#0d1117]">AB</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Arbitrage Bot</h1>
              <p className="text-xs text-gray-400">Trading Dashboard</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = pathname === item.href || pathname?.startsWith(item.href);
              return (
                <button
                  key={item.id}
                  onClick={() => handleNav(item.href)}
                  className={`w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 text-left ${
                    isActive
                      ? 'bg-gradient-to-r from-[#4ade80]/20 to-[#38bdf8]/20 text-[#4ade80] border border-[#4ade80]/30 shadow-glow-green'
                      : 'text-gray-400 hover:bg-[#1e293b] hover:text-white'
                  }`}
                >
                  <span className={isActive ? 'text-[#4ade80]' : 'text-gray-400'}>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="border-t border-[#1e293b] p-4">
            <div className="rounded-lg bg-[#1e293b]/50 p-3 text-xs">
              <div className="mb-1 font-semibold text-white">Version 1.1.0</div>
              <div className="text-gray-400">Production Mode</div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
