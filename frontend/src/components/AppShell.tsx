'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === '/login' || pathname === '/signup';

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className={`${isAuthPage ? 'ml-0' : 'ml-64'} flex-1 p-8`}>
        {children}
      </main>
    </div>
  );
}
