'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getAuthToken } from '@/lib/api';

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = getAuthToken();
    const isAuthPage = pathname === '/login' || pathname === '/signup';

    if (!token && !isAuthPage) {
      // Not logged in and not on auth page - redirect to login
      router.push('/login');
    } else if (token && isAuthPage) {
      // Logged in but on auth page - redirect to home
      router.push('/');
    } else {
      setChecking(false);
    }
  }, [pathname, router]);

  // Show loading while checking auth
  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}
