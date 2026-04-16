import { useState, FormEvent } from 'react'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: Hero */}
      <div
        className="hidden lg:flex lg:w-1/2 relative bg-cover bg-center"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?w=1200&q=80')",
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
          <div className="animate-slideUp">
            <blockquote className="text-xl font-light leading-relaxed italic max-w-md">
              "Golf is the closest game to the game we call life. You get bad breaks from good shots; you get good breaks from bad shots — but you have to play the ball where it lies."
            </blockquote>
            <p className="mt-3 text-sm text-white/50">— Bobby Jones</p>
          </div>
          <div className="text-xs text-white/30">
            © 2026 Fairway Elite. All rights reserved.
          </div>
        </div>
      </div>

      {/* Right: Form */}
      <div className="flex-1 flex items-center justify-center bg-surface px-6">
        <div className="w-full max-w-sm animate-slideUp">
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center">
              <span className="text-sm">⛳</span>
            </div>
            <h1 className="text-xl font-black text-green-900">Fairway Elite</h1>
          </div>

          <h2 className="text-2xl font-bold text-gray-900">Welcome back</h2>
          <p className="text-sm text-gray-500 mt-1 mb-7">Sign in to your Elite account</p>

          {error && (
            <div className="mb-4 px-4 py-3 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-2xl animate-slideDown">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                Email
              </label>
              <input
                id="login-email"
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
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
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
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-green-900 to-green-800 text-white py-3 rounded-xl font-semibold text-sm hover:shadow-glow transition-all duration-300 disabled:opacity-60 mt-2 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <p className="text-sm text-center text-gray-500 mt-6">
            Don't have an account?{' '}
            <Link
              to="/signup"
              className="text-green-900 font-semibold hover:underline"
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
