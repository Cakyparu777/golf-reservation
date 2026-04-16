import { useEffect, useState, type ElementType, type FormEvent, type ReactNode } from 'react'
import { Bell, Car, MapPin, TrainFront, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function SettingsPage() {
  const { user, refreshProfile, updateProfile } = useAuth()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [homeArea, setHomeArea] = useState('')
  const [travelMode, setTravelMode] = useState<'train' | 'car' | 'either'>('train')
  const [maxTravelMinutes, setMaxTravelMinutes] = useState(60)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

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
        if (active) setError('Could not refresh your profile right now.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [refreshProfile])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await updateProfile({
        name,
        phone,
        homeArea,
        travelMode,
        maxTravelMinutes,
      })
      setMessage('Travel preferences saved. New recommendations will use them right away.')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Profile update failed.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="px-8 py-6 max-w-4xl">
      <div className="flex items-start justify-between gap-6 mb-6">
        <div>
          <p className="text-xs font-bold text-[#c8922a] uppercase tracking-widest mb-1">Profile Settings</p>
          <h1 className="text-2xl font-bold text-gray-900">Travel Preferences</h1>
          <p className="text-sm text-gray-500 mt-1 max-w-2xl">
            Your assistant uses these details to rank nearby courses and automatically avoid rain or winds above 20 km/h.
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-[#e4eadf] px-4 py-3 min-w-64 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#1a3d2b]">Default weather rule</p>
          <p className="text-sm text-gray-600 mt-1">Rainy or windy tee times are filtered out unless you explicitly ask for them.</p>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_280px] gap-6">
        <form onSubmit={handleSubmit} className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-full bg-[#eef5ed] flex items-center justify-center">
              <User size={20} className="text-[#1a3d2b]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Member Profile</h2>
              <p className="text-sm text-gray-500">Keep your booking defaults accurate so recommendations feel personal.</p>
            </div>
          </div>

          {loading && <p className="text-sm text-gray-400 mb-4">Refreshing your profile...</p>}
          {error && <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}
          {message && <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{message}</div>}

          <div className="grid grid-cols-2 gap-4">
            <Field label="Full Name">
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10"
                required
              />
            </Field>

            <Field label="Phone">
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="Optional"
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4 mt-4">
            <Field label="Home Area or Nearest Station">
              <div className="relative">
                <MapPin size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  value={homeArea}
                  onChange={(event) => setHomeArea(event.target.value)}
                  placeholder="Adachi-ku or Kita-Senju"
                  className="w-full rounded-xl border border-gray-200 bg-white pl-10 pr-4 py-3 text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10"
                  required
                />
              </div>
            </Field>

            <Field label="Max Travel Time">
              <select
                value={maxTravelMinutes}
                onChange={(event) => setMaxTravelMinutes(Number(event.target.value))}
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10"
              >
                {[30, 45, 60, 75, 90, 120, 150].map((minutes) => (
                  <option key={minutes} value={minutes}>{minutes} min</option>
                ))}
              </select>
            </Field>
          </div>

          <div className="mt-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">Travel Mode</p>
            <div className="grid grid-cols-3 gap-3">
              <TravelModeCard
                active={travelMode === 'train'}
                label="Train"
                sub="Best for city access"
                icon={TrainFront}
                onClick={() => setTravelMode('train')}
              />
              <TravelModeCard
                active={travelMode === 'car'}
                label="Car"
                sub="Better for wider range"
                icon={Car}
                onClick={() => setTravelMode('car')}
              />
              <TravelModeCard
                active={travelMode === 'either'}
                label="Either"
                sub="Stay flexible"
                icon={Bell}
                onClick={() => setTravelMode('either')}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving || loading}
            className="mt-6 rounded-2xl bg-[#1a3d2b] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#1e4d33] disabled:opacity-60"
          >
            {saving ? 'Saving changes...' : 'Save travel profile'}
          </button>
        </form>

        <div className="space-y-4">
          <div className="rounded-3xl bg-white p-5 shadow-sm border border-gray-100">
            <p className="text-xs font-bold uppercase tracking-widest text-[#c8922a]">How It Helps</p>
            <ul className="mt-3 space-y-3 text-sm text-gray-600 leading-relaxed">
              <li>Nearest-course suggestions use your saved area automatically.</li>
              <li>Recommendation ranking considers travel time before surfacing a course.</li>
              <li>The assistant keeps your travel mode in context for follow-up questions.</li>
            </ul>
          </div>

          <div className="rounded-3xl bg-[#1a3d2b] p-5 text-white shadow-sm">
            <p className="text-xs font-bold uppercase tracking-widest text-[#d8b96a]">Assistant Default</p>
            <p className="mt-3 text-sm leading-relaxed text-white/85">
              "Find me the closest good-weather tee time tomorrow" now automatically uses your saved home area, travel mode, and travel-time cap.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</span>
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
      className={`rounded-2xl border px-4 py-4 text-left transition-colors ${
        active
          ? 'border-[#1a3d2b] bg-[#f2f7f1]'
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <Icon size={18} className={active ? 'text-[#1a3d2b]' : 'text-gray-500'} />
      <p className="mt-3 text-sm font-semibold text-gray-900">{label}</p>
      <p className="mt-1 text-xs text-gray-500">{sub}</p>
    </button>
  )
}
