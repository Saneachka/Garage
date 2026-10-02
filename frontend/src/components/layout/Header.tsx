import { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { Menu, Bell, Sun, Moon, LogOut, User, ChevronDown } from 'lucide-react';
import { cn } from '../utils/helpers';

export function Header() {
  const { user, logout } = useAuthStore();
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-secondary-200">
      <div className="flex h-full items-center justify-between px-4 lg:px-6">
        {/* Mobile menu button */}
        <button
          className="lg:hidden p-2 rounded-lg text-secondary-500 hover:bg-secondary-100"
          onClick={() => window.dispatchEvent(new CustomEvent('toggle-sidebar'))}
        >
          <Menu className="h-6 w-6" />
        </button>

        {/* Page title - will be set by pages */}
        <div className="flex-1 lg:flex-none" />

        {/* Right side */}
        <div className="flex items-center gap-4">
          {/* Notifications */}
          <button className="relative p-2 rounded-lg text-secondary-500 hover:bg-secondary-100">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1 right-1 h-4 w-4 rounded-full bg-red-500 text-xs text-white flex items-center justify-center">3</span>
          </button>

          {/* Theme toggle */}
          <button className="p-2 rounded-lg text-secondary-500 hover:bg-secondary-100">
            <Sun className="h-5 w-5" />
          </button>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-secondary-100"
            >
              <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                <span className="text-sm font-medium text-primary-700">
                  {user?.full_name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="hidden md:block text-sm font-medium text-secondary-700">
                {user?.full_name}
              </span>
              <ChevronDown className="h-4 w-4 text-secondary-500" />
            </button>

            {isProfileOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setIsProfileOpen(false)}
                />
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-secondary-200 py-1 z-50">
                  <Link
                    to="/profile"
                    className="flex items-center gap-2 px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-50"
                    onClick={() => setIsProfileOpen(false)}
                  >
                    <User className="h-4 w-4" />
                    Profile
                  </Link>
                  <hr className="my-1 border-secondary-100" />
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}