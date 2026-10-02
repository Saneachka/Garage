import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

export function MainLayout() {
  const { isAuthenticated, isLoading } = useAuthStore();

  // Handle mobile sidebar toggle
  useEffect(() => {
    const handleToggle = () => {
      window.dispatchEvent(new CustomEvent('sidebar-toggled'));
    };
    window.addEventListener('toggle-sidebar', handleToggle);
    return () => window.removeEventListener('toggle-sidebar', handleToggle);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-secondary-50">
      <Sidebar />
      <div className="lg:pl-64">
        <Header />
        <main className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}