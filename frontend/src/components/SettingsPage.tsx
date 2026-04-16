import { useEffect, useState, type ElementType, type FormEvent, type ReactNode } from 'react'
import { Bell, Car, MapPin, TrainFront, User, Save, Loader2, ShieldCheck, Zap } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function SettingsPage() {
  const { user, refreshProfile, updateProfile } = useAuth()
  const { addToast } = useToast()
  
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [homeArea, setHomeArea] = useState('')
  const [travelMode, setTravelMode] = useState<'train' | 'car' | 'either'>('train')
  const [maxTravelMinutes, setMaxTravelMinutes] = useState(60)
  
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!user) return
    setName(user.name)
    setPhone(user.phone ?? '')
    setHomeArea(user.home_area)
    setTravelMode(user.travel_mode)
    setMaxTravelMinutes(user.max_travel_minutes)
  }, [user])

  useEffect(() => {
    let active = true
    setLoading(true)
    refreshProfile()
      .catch(() => {
        if (active) addToast('error', 'Could not refresh your profile right now.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [refreshProfile, addToast])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      await updateProfile({
        name,
        phone,
        homeArea,
        travelMode,
        maxTravelMinutes,
      })
      addToast('success', 'Travel preferences saved successfully.')
    } catch (err: unknown) {
      addToast('error', err instanceof Error ? err.message : 'Profile update failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="px-4 md:px-8 py-6 max-w-5xl animate-fadeIn pb-24 md:pb-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-8 animate-slideInLeft">
        <div>
          <p className="text-[10px] font-bold text-gold-500 uppercase tracking-[.2em] mb-1">Profile Settings</p>
          <h1 className="text-2xl md:text-3xl font-extrabold text-green-900 tracking-tight">Travel Preferences</h1>
          <p className="text-sm text-gray-500 mt-1 max-w-lg">
            Your assistant uses these details to rank nearby courses and automatically avoid rain or winds above 20 km/h.
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-100 px-5 py-4 min-w-[280px] shadow-soft animate-slideInRight flex gap-4">
          <div className="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center shrink-0">
            <ShieldCheck size={20} className="text-green-700" />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-green-900">Default weather rule</p>
            <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">Rainy or windy conditions are automatically filtered out initially.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-8 items-start">
        <form onSubmit={handleSubmit} className="bg-white rounded-[2rem] p-6 shadow-soft border border-gray-100/60 animate-slideUp stagger-1 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-green-900/[0.02] rounded-bl-full pointer-events-none" />
          
          <div className="flex items-center gap-4 mb-8">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center text-white shadow-soft">
              <User size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Member Identity</h2>
              <p className="text-sm text-gray-500 font-medium">Keep your details accurate for the concierge.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label="Full Name">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm font-semibold outline-none focus:bg-white focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
                required
              />
            </Field>

            <Field label="Phone Number">
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="Optional"
                className="w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm font-semibold outline-none focus:bg-white focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
              />
            </Field>
          </div>

          <div className="h-px bg-gray-100 my-8 w-full" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
            <Field label="Home Area or Nearest Station">
              <div className="relative">
                <MapPin size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  value={homeArea}
                  onChange={(event) => setHomeArea(event.target.value)}
                  placeholder="Adachi-ku or Kita-Senju"
                  className="w-full rounded-xl border border-gray-200 bg-gray-50/50 pl-10 pr-4 py-3 text-sm font-semibold outline-none focus:bg-white focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
                  required
                />
              </div>
            </Field>

            <Field label="Max Travel Time (One Way)">
              <div className="relative focus-within:ring-2 focus-within:ring-green-900/10 rounded-xl transition-shadow">
                <select
                  value={maxTravelMinutes}
                  onChange={(event) => setMaxTravelMinutes(Number(event.target.value))}
                  className="w-full rounded-xl border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm font-semibold outline-none focus:bg-white focus:border-green-900 transition-colors appearance-none"
                >
                  {[30, 45, 60, 75, 90, 120, 150].map((minutes) => (
                    <option key={minutes} value={minutes}>{minutes} minutes max</option>
                  ))}
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none border-l-[5px] border-r-[5px] border-t-[5px] border-transparent border-t-gray-500" />
              </div>
            </Field>
          </div>

          <div className="mb-4">
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">Preferred Transit Mode</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <TravelModeCard
                active={travelMode === 'train'}
                label="Train"
                sub="Fast city links"
                icon={TrainFront}
                onClick={() => setTravelMode('train')}
              />
              <TravelModeCard
                active={travelMode === 'car'}
                label="Car"
                sub="Wider radius"
                icon={Car}
                onClick={() => setTravelMode('car')}
              />
              <TravelModeCard
                active={travelMode === 'either'}
                label="Either"
                sub="Most flexible"
                icon={Bell} /* Kept icon as Bell from original, could be Map or Navigation */
                onClick={() => setTravelMode('either')}
              />
            </div>
          </div>

          <div className="mt-8 flex justify-end">
            <button
              type="submit"
              disabled={saving || loading}
              className="w-full md:w-auto rounded-xl bg-gradient-to-r from-green-900 to-green-800 px-8 py-3.5 text-sm font-bold text-white transition-all duration-300 hover:shadow-glow disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Saving...
                </>
              ) : (
                <>
                  <Save size={16} /> Save Profile
                </>
              )}
            </button>
          </div>
        </form>

        <div className="space-y-4 animate-slideUp stagger-2">
          <div className="rounded-[1.5rem] bg-white p-6 shadow-soft border border-gray-100">
            <p className="text-[10px] font-bold uppercase tracking-widest text-gold-500 mb-1">Algorithm Insights</p>
            <h3 className="text-base font-bold text-gray-900 mb-3">How the Caddie Uses This</h3>
            <ul className="space-y-3">
              {[
                'Proximity scoring uses your saved home station automatically.',
                'Travel time estimates factor mode explicitly.',
                'Contextual follow-ups maintain your travel method preference.'
              ].map((item, i) => (
                <li key={i} className="flex gap-2.5 text-sm text-gray-600 leading-relaxed font-medium">
                  <span className="text-green-600 mt-1 shrink-0"><CheckCircle size={14} /></span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-[1.5rem] bg-gradient-to-br from-green-900 to-green-950 p-6 text-white shadow-soft relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-white/[0.05] rounded-bl-full" />
            <div className="flex items-center gap-2 mb-2">
              <Zap size={14} className="text-gold-400" />
              <p className="text-[10px] font-bold uppercase tracking-widest text-gold-400">Assistant Demo</p>
            </div>
            <p className="text-sm font-medium leading-relaxed text-white/90 italic">
              "Find me the closest good-weather tee time tomorrow."
            </p>
            <div className="mt-3 bg-white/10 rounded-lg p-3 border border-white/5 backdrop-blur-sm">
              <p className="text-xs text-white/70 flex items-center gap-1.5 font-medium">
                <CheckCircle size={12} className="text-gold-400" /> Now automatically uses your area & limits.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block group">
      <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-widest text-gray-400 transition-colors group-focus-within:text-green-900">
        {label}
      </span>
      {children}
    </label>
  )
}

function TravelModeCard({
  active,
  label,
  sub,
  icon: Icon,
  onClick,
}: {
  active: boolean
  label: string
  sub: string
  icon: ElementType
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl border-2 px-4 py-4 text-left transition-all duration-200 group ${
        active
          ? 'border-green-900 bg-green-50 shadow-sm transform scale-[1.02]'
          : 'border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50'
      }`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 transition-colors ${
        active ? 'bg-green-900 text-white' : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'
      }`}>
        <Icon size={16} />
      </div>
      <p className={`text-sm font-bold ${active ? 'text-green-900' : 'text-gray-900'}`}>{label}</p>
      <p className={`mt-0.5 text-[11px] font-medium ${active ? 'text-green-700' : 'text-gray-500'}`}>{sub}</p>
    </button>
  )
}

// Small UI helper
function CheckCircle({ size, className }: { size: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  )
}
