import { Link, useLocation, NavLink } from 'react-router-dom';
import { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { Menu, X, LogOut, User, LayoutDashboard, Car, Wrench, Calendar, FileText, Package, Users, Settings, ChevronDown } from 'lucide-react';
import { cn } from '../utils/helpers';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['admin', 'manager', 'mechanic', 'customer'] },
  { name: 'Vehicles', href: '/vehicles', icon: Car, roles: ['admin', 'manager', 'mechanic', 'customer'] },
  { name: 'Services', href: '/services', icon: Wrench, roles: ['admin', 'manager', 'mechanic', 'customer'] },
  { name: 'Appointments', href: '/appointments', icon: Calendar, roles: ['admin', 'manager', 'mechanic', 'customer'] },
  { name: 'Orders', href: '/orders', icon: FileText, roles: ['admin', 'manager', 'mechanic', 'customer'] },
  { name: 'Invoices', href: '/invoices', icon: FileText, roles: ['admin', 'manager', 'mechanic', 'customer'] },
  { name: 'Parts', href: '/parts', icon: Package, roles: ['admin', 'manager'] },
  { name: 'Users', href: '/users', icon: Users, roles: ['admin', 'manager'] },
  { name: 'Settings', href: '/settings', icon: Settings, roles: ['admin', 'manager'] },
];

export function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);

  const filteredNav = navigation.filter((item) =>
    user ? item.roles.includes(user.role) : false
  );

  return (
    <>
      {/* Mobile sidebar overlay */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 lg:hidden transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={() => setIsOpen(false)}
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white border-r border-secondary-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 items-center justify-between px-4 border-b border-secondary-200 lg:justify-center">
          <Link to="/dashboard" className="flex items-center gap-2 text-xl font-bold text-primary-600">
            <Car className="h-8 w-8" />
            <span>AutoService</span>
          </Link>
          <button
            className="lg:hidden p-2 rounded-lg text-secondary-500 hover:bg-secondary-100"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {filteredNav.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                )}
                onClick={() => setIsOpen(false)}
              >
                <Icon className="h-5 w-5" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-secondary-200">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-secondary-900 truncate">{user?.full_name}</p>
              <p className="text-xs text-secondary-500 truncate">{user?.email}</p>
            </div>
          </div>
          <div className="mt-2 space-y-1">
            <Link
              to="/profile"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900"
              onClick={() => setIsOpen(false)}
            >
              <User className="h-5 w-5" />
              Profile
            </Link>
            <button
              onClick={logout}
              className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-5 w-5" />
              Sign out
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}