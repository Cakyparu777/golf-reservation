import { Bot, Flag, Calendar, Settings, LogOut } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import type { Page } from '../App'
import { useAuth } from '../context/AuthContext'

const navItems: { id: Page; label: string; icon: React.ElementType; to: string }[] = [
  { id: 'assistant', label: 'Assistant', icon: Bot, to: '/assistant' },
  { id: 'teetimes', label: 'Tee Times', icon: Flag, to: '/tee-times' },
  { id: 'mygolf', label: 'My Golf', icon: Calendar, to: '/my-golf' },
  { id: 'settings', label: 'Settings', icon: Settings, to: '/settings' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <aside className="w-52 glass-dark flex flex-col h-full shrink-0 animate-fadeIn">
      {/* Logo */}
      <div className="px-5 pt-6 pb-4 flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-700 to-green-900 flex items-center justify-center shadow-sm">
          <span className="text-sm">⛳</span>
        </div>
        <span className="text-white font-bold text-base tracking-tight">Fairway Elite</span>
      </div>

      {/* User Profile */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-2.5 bg-white/[.07] rounded-2xl px-3 py-2.5">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-gold-500 to-gold-300 flex items-center justify-center text-green-950 text-xs font-bold shrink-0 shadow-sm">
            {user?.name.charAt(0).toUpperCase() ?? 'E'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.name ?? 'Member'}</p>
            <p className="text-[10px] text-white/40 tracking-wide uppercase font-medium">Elite Member</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent mx-4 mb-2" />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {navItems.map(({ id, label, icon: Icon, to }) => (
          <NavLink
            key={id}
            to={to}
            className={({ isActive }) =>
              `w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 relative ${
                isActive
                  ? 'text-white bg-white/[.12] shadow-sm'
                  : 'text-white/50 hover:text-white/80 hover:bg-white/[.05]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-gold-500 rounded-r-full transition-all" />
                )}
                <Icon size={16} strokeWidth={1.8} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-4 pb-6 space-y-2">
        <NavLink
          to="/tee-times"
          className="block w-full bg-gradient-to-r from-gold-500 to-gold-400 text-green-950 rounded-xl py-2.5 text-sm font-bold hover:shadow-glow transition-all duration-300 text-center"
        >
          Book Now
        </NavLink>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-1.5 text-xs text-white/25 hover:text-white/60 py-1.5 transition-colors"
        >
          <LogOut size={12} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
