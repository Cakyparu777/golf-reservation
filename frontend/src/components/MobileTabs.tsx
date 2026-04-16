import { Bot, Flag, Calendar, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import type { Page } from '../App'

const navItems: { id: Page; label: string; icon: React.ElementType; to: string }[] = [
  { id: 'assistant', label: 'Assistant', icon: Bot, to: '/assistant' },
  { id: 'teetimes', label: 'Tee Times', icon: Flag, to: '/tee-times' },
  { id: 'mygolf', label: 'My Golf', icon: Calendar, to: '/my-golf' },
  { id: 'settings', label: 'Settings', icon: Settings, to: '/settings' },
]

export default function MobileTabs() {
  return (
    <nav className="mobile-tabs fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-xl border-t border-gray-100 z-50 px-2 pb-[env(safe-area-inset-bottom)]">
      <div className="flex items-center justify-around">
        {navItems.map(({ id, label, icon: Icon, to }) => (
          <NavLink
            key={id}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 py-2 px-3 text-[10px] font-medium transition-colors ${
                isActive
                  ? 'text-green-900'
                  : 'text-gray-400'
              }`
            }
          >
            <Icon size={20} strokeWidth={1.6} />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
