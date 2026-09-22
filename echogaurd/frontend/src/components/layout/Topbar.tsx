import { Bell, Moon, Shield, Sun } from 'lucide-react'
import { useAuth } from '../../context/useAuth'
import { useTheme } from '../../context/ThemeContext'

export default function Topbar() {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const initials = user?.display_name?.trim().split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'U'

  return (
    <header className="sticky top-0 z-30 flex min-h-16 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 backdrop-blur sm:px-6 md:px-8">
      <div>
        <p className="text-xs uppercase tracking-widest text-slate-500">
          Security Operations
        </p>

        <p className="font-medium text-slate-200">
          Communication Security Center
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700 sm:flex">
          <Shield className="h-3.5 w-3.5" />
          Protection Active
        </div>

        <button type="button" onClick={toggleTheme} className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-900 hover:text-slate-200" aria-label="Toggle theme">
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
        <button type="button" className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-900 hover:text-slate-200" aria-label="Notifications">
          <Bell className="h-5 w-5" />
        </button>

        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-slate-200">{user?.display_name || 'Account'}</p>
          <p className="text-xs text-slate-500">@{user?.username || 'user'}</p>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white" aria-label={user?.display_name || 'Account'}>
          {initials}
        </div>
      </div>
    </header>
  )
}