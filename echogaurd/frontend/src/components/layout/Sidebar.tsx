// Removed unused React import
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, ShieldAlert, Phone, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/useAuth';
import { Avatar } from '../ui/Avatar';

const navigation = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Contacts', path: '/contacts', icon: Users },
  { name: 'Threats', path: '/threats', icon: ShieldAlert },
];

export default function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 border-r border-slate-800 bg-slate-950 md:block">
      <div className="flex h-full flex-col justify-between">
        {/* Logo and navigation */}
        <div>
          <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-6">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10">
              <ShieldCheck className="h-5 w-5 text-cyan-400" />
            </div>
            <div>
              <p className="font-bold tracking-tight">Saksham 2.0</p>
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Communication security</p>
            </div>
          </div>
          <nav className="flex-1 space-y-1 p-4">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Security</p>
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    [
                      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition',
                      isActive
                        ? 'bg-cyan-500/10 text-cyan-400'
                        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200',
                    ].join(' ')
                  }
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </NavLink>
              );
            })}
            {/* Start Call button */}
            <div
              className="mt-6 flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5 text-sm text-slate-500"
              title="Start a call from Contacts"
            >
              <Phone className="h-4 w-4" />
              Start from Contacts
            </div>
          </nav>
        </div>
          {/* User profile */}
        <div className="border-t border-slate-800 p-4">
            <div className="flex items-center gap-2">
              <Avatar fallback={user?.display_name?.[0] ?? 'U'} size={32} className="bg-slate-700" />
              <div className="flex flex-col">
                <span className="text-sm font-medium text-slate-200">{user?.display_name || 'User'}</span>
                <span className="text-xs text-slate-400">@{user?.username || 'user'}</span>
              </div>
          </div>
          <button
            onClick={logout}
            className="mt-3 w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-center text-sm text-slate-700 hover:bg-slate-50"
          >
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}