import { User, Bell, Lock, CreditCard } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="px-8 py-6 max-w-2xl">
      <h1 className="text-xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="space-y-3">
        {[
          { icon: User, label: 'Profile', sub: 'Manage your account details' },
          { icon: Bell, label: 'Notifications', sub: 'Tee time reminders and alerts' },
          { icon: Lock, label: 'Privacy & Security', sub: 'Password and access settings' },
          { icon: CreditCard, label: 'Billing', sub: 'Payment methods and history' },
        ].map(({ icon: Icon, label, sub }) => (
          <button
            key={label}
            className="w-full bg-white rounded-2xl p-4 flex items-center gap-4 shadow-sm hover:shadow-md transition-shadow text-left"
          >
            <div className="w-10 h-10 rounded-full bg-[#f0f5f0] flex items-center justify-center shrink-0">
              <Icon size={18} className="text-[#1a3d2b]" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">{label}</p>
              <p className="text-xs text-gray-500">{sub}</p>
            </div>
            <span className="ml-auto text-gray-300">›</span>
          </button>
        ))}
      </div>
    </div>
  )
}
