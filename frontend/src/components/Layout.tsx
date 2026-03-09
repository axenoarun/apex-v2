import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { listNotifications } from '../api/endpoints';
import {
  FolderKanban,
  Bell,
  Lightbulb,
  LogOut,
  Zap,
  Shield,
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { to: '/projects', label: 'Projects', icon: FolderKanban },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/improvements', label: 'Improvements', icon: Lightbulb },
  { to: '/admin', label: 'Admin', icon: Shield },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const { data: unread } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => listNotifications(true).then((r) => r.data.length),
    refetchInterval: 30000,
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 text-white flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Zap size={24} className="text-blue-400" />
            <span className="text-lg font-bold">APEX v2</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">AA → CJA Migration OS</p>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                )
              }
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === 'Notifications' && unread && unread > 0 && (
                <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {unread}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700">
          <div className="text-sm font-medium truncate">{user?.name}</div>
          <div className="text-xs text-slate-400 truncate">{user?.email}</div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-white mt-2 transition-colors"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
