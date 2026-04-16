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
    <aside className="w-48 bg-white flex flex-col h-full border-r border-gray-100 shrink-0">
      <div className="px-5 pt-6 pb-4">
        <span className="text-[#1a3d2b] font-bold text-lg tracking-tight">Fairway Elite</span>
      </div>

      <div className="px-4 pb-5">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-full bg-[#1a3d2b] flex items-center justify-center text-white text-xs font-semibold shrink-0">
            {user?.name.charAt(0).toUpperCase() ?? 'E'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate">{user?.name ?? 'Member'}</p>
            <p className="text-xs text-gray-500 truncate">Elite Member Status</p>
          </div>
        </div>
      </div>

      <div className="h-px bg-gray-100 mx-4 mb-2" />

      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {navItems.map(({ id, label, icon: Icon, to }) => (
          <NavLink
            key={id}
            to={to}
            className={({ isActive }) =>
              `w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors relative ${
                isActive
                  ? 'text-[#1a3d2b] bg-[#f0f5f0]'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[#1a3d2b] rounded-r" />
                )}
                <Icon size={16} strokeWidth={1.8} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 pb-6 space-y-2">
        <NavLink
          to="/tee-times"
          className="block w-full bg-[#1a3d2b] text-white rounded-full py-2.5 text-sm font-semibold hover:bg-[#1e4d33] transition-colors text-center"
        >
          Book Now
        </NavLink>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 py-1 transition-colors"
        >
          <LogOut size={12} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
