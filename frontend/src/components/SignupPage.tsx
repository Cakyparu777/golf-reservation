import { useState, FormEvent } from 'react'
import { Eye, EyeOff, Check, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function SignupPage() {
  const { register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [homeArea, setHomeArea] = useState('Adachi-ku')
  const [travelMode, setTravelMode] = useState<'train' | 'car' | 'either'>('train')
  const [maxTravelMinutes, setMaxTravelMinutes] = useState(60)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const passwordStrength = password.length >= 8 ? 'strong' : password.length >= 6 ? 'fair' : 'weak'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register({
        name,
        email,
        password,
        homeArea,
        travelMode,
        maxTravelMinutes,
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const perks = [
    'Access to 500+ premium courses worldwide',
    'AI caddie powered by your performance data',
    'Elite member perks and exclusive invitations',
  ]

  return (
    <div className="min-h-screen flex">
      {/* Left: Hero */}
      <div
        className="hidden lg:flex lg:w-1/2 relative bg-cover bg-center"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1535131749006-b7f58c99034b?w=1200&q=80')",
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-green-950/80 via-green-900/60 to-green-800/70" />
        <div className="relative z-10 flex flex-col justify-between p-10 text-white w-full">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center">
              <span className="text-lg">⛳</span>
            </div>
            <h1 className="text-xl font-black tracking-tight">Fairway Elite</h1>
          </div>
          <div className="space-y-4">
            {perks.map((perk, i) => (
              <div
                key={perk}
                className={`flex items-center gap-3 animate-slideUp stagger-${i + 1}`}
              >
                <div className="w-6 h-6 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center shrink-0">
                  <Check size={12} color="white" />
                </div>
                <span className="text-sm text-white/80">{perk}</span>
              </div>
            ))}
          </div>
          <div className="text-xs text-white/30">© 2026 Fairway Elite. All rights reserved.</div>
        </div>
      </div>

      {/* Right: Form */}
      <div className="flex-1 flex items-center justify-center bg-surface px-6 py-8 overflow-y-auto">
        <div className="w-full max-w-md animate-slideUp">
          <div className="lg:hidden mb-6 flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center">
              <span className="text-sm">⛳</span>
            </div>
            <h1 className="text-xl font-black text-green-900">Fairway Elite</h1>
          </div>

          <h2 className="text-2xl font-bold text-gray-900">Create your account</h2>
          <p className="text-sm text-gray-500 mt-1 mb-6">Join the Elite membership today</p>

          {error && (
            <div className="mb-4 px-4 py-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-2xl animate-slideDown">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Full Name
              </label>
              <input
                id="signup-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Smith"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Email
              </label>
              <input
                id="signup-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="pro@example.com"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {password && (
                <div className="mt-2 flex gap-1">
                  {['weak', 'fair', 'strong'].map((level, i) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full transition-all duration-500 ${
                        (passwordStrength === 'weak' && i === 0) ||
                        (passwordStrength === 'fair' && i <= 1) ||
                        passwordStrength === 'strong'
                          ? passwordStrength === 'strong'
                            ? 'bg-emerald-500'
                            : passwordStrength === 'fair'
                            ? 'bg-amber-400'
                            : 'bg-rose-400'
                          : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Home Area or Nearest Station
              </label>
              <input
                id="signup-home-area"
                type="text"
                required
                value={homeArea}
                onChange={(e) => setHomeArea(e.target.value)}
                placeholder="Adachi-ku or Kita-Senju"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  Travel Mode
                </label>
                <select
                  id="signup-travel-mode"
                  value={travelMode}
                  onChange={(e) => setTravelMode(e.target.value as 'train' | 'car' | 'either')}
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
                >
                  <option value="train">Train</option>
                  <option value="car">Car</option>
                  <option value="either">Either</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  Max Travel Time
                </label>
                <select
                  id="signup-max-travel"
                  value={maxTravelMinutes}
                  onChange={(e) => setMaxTravelMinutes(Number(e.target.value))}
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-green-900 focus:ring-2 focus:ring-green-900/10 transition-all"
                >
                  {[45, 60, 75, 90, 120].map((minutes) => (
                    <option key={minutes} value={minutes}>
                      {minutes} min
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="rounded-2xl bg-surface-muted border border-green-900/10 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-green-900">Default booking preference</p>
              <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                We automatically avoid rainy tee times and wind above 20 km/h unless you tell the assistant otherwise.
              </p>
            </div>

            <button
              id="signup-submit"
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-green-900 to-green-800 text-white py-3 rounded-xl font-semibold text-sm hover:shadow-glow transition-all duration-300 disabled:opacity-60 mt-2 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Creating account…
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <p className="text-sm text-center text-gray-500 mt-6">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-green-900 font-semibold hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
