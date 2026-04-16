import { useState, FormEvent } from 'react'
import { Eye, EyeOff, Check } from 'lucide-react'
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

  return (
    <div className="min-h-screen flex">
      {/* Left: Golf image */}
      <div
        className="hidden lg:flex lg:w-1/2 relative bg-cover bg-center"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1535131749006-b7f58c99034b?w=1200&q=80')",
        }}
      >
        <div className="absolute inset-0 bg-[#1a3d2b]/60" />
        <div className="relative z-10 flex flex-col justify-between p-10 text-white">
          <h1 className="text-2xl font-black tracking-tight">Fairway Elite</h1>
          <div className="space-y-4">
            {[
              'Access to 500+ premium courses worldwide',
              'AI caddie powered by your performance data',
              'Elite member perks and exclusive invitations',
            ].map((perk) => (
              <div key={perk} className="flex items-center gap-3">
                <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center shrink-0">
                  <Check size={11} color="white" />
                </div>
                <span className="text-sm text-white/90">{perk}</span>
              </div>
            ))}
          </div>
          <div className="text-sm text-white/50">© 2024 Fairway Elite. All rights reserved.</div>
        </div>
      </div>

      {/* Right: Form */}
      <div className="flex-1 flex items-center justify-center bg-[#f4f6f0] px-6">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8">
            <h1 className="text-2xl font-black text-[#1a3d2b]">Fairway Elite</h1>
          </div>

          <h2 className="text-2xl font-bold text-gray-900">Create your account</h2>
          <p className="text-sm text-gray-500 mt-1 mb-7">Join the Elite membership today</p>

          {error && (
            <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Full Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Smith"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="pro@example.com"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 6 characters"
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10 transition pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {password && (
                <div className="mt-2 flex gap-1">
                  {['weak', 'fair', 'strong'].map((level, i) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        (passwordStrength === 'weak' && i === 0) ||
                        (passwordStrength === 'fair' && i <= 1) ||
                        passwordStrength === 'strong'
                          ? passwordStrength === 'strong'
                            ? 'bg-green-500'
                            : passwordStrength === 'fair'
                            ? 'bg-yellow-400'
                            : 'bg-red-400'
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
                type="text"
                required
                value={homeArea}
                onChange={(e) => setHomeArea(e.target.value)}
                placeholder="Adachi-ku or Kita-Senju"
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10 transition"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  Travel Mode
                </label>
                <select
                  value={travelMode}
                  onChange={(e) => setTravelMode(e.target.value as 'train' | 'car' | 'either')}
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10 transition"
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
                  value={maxTravelMinutes}
                  onChange={(e) => setMaxTravelMinutes(Number(e.target.value))}
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl text-sm outline-none focus:border-[#1a3d2b] focus:ring-2 focus:ring-[#1a3d2b]/10 transition"
                >
                  {[45, 60, 75, 90, 120].map((minutes) => (
                    <option key={minutes} value={minutes}>
                      {minutes} min
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="rounded-2xl bg-[#f8fbf4] border border-[#dbe6d4] px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#1a3d2b]">Default booking preference</p>
              <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                We automatically avoid rainy tee times and wind above 20 km/h unless you tell the assistant otherwise.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#1a3d2b] text-white py-3 rounded-xl font-semibold text-sm hover:bg-[#1e4d33] transition disabled:opacity-60 mt-2"
            >
              {loading ? 'Creating account…' : 'Create Account'}
            </button>
          </form>

          <p className="text-sm text-center text-gray-500 mt-6">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-[#1a3d2b] font-semibold hover:underline"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
