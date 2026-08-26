'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getAuthToken, setAuthToken } from '@/lib/api';

const navItems = [
  { href: '/', label: 'Dashboard', icon: '📊' },
  { href: '/jobs', label: 'Jobs', icon: '⚡' },
  { href: '/workflows', label: 'Workflows', icon: '🔀' },
  { href: '/workers', label: 'Workers', icon: '🖥️' },
  { href: '/logs', label: 'Logs', icon: '📝' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!getAuthToken());
  }, [pathname]);

  const handleLogout = () => {
    setAuthToken(null);
    setIsLoggedIn(false);
    router.push('/login');
  };

  // Don't show sidebar on login/signup pages
  if (pathname === '/login' || pathname === '/signup') {
    return null;
  }

  // Don't show sidebar if not logged in
  if (!isLoggedIn) {
    return null;
  }

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 bg-slate-900 border-r border-slate-700">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-slate-700 px-6">
          <span className="text-2xl">🐝</span>
          <span className="text-xl font-bold text-white">TaskMesh</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const isActive = item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer with user info and logout */}
        <div className="border-t border-slate-700 px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-xs text-slate-400">System Online</span>
            </div>
            <button
              onClick={handleLogout}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
