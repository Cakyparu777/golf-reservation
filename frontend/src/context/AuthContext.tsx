import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

interface AuthUser {
  id: number
  name: string
  email: string
  phone?: string | null
  home_area: string
  travel_mode: 'train' | 'car' | 'either'
  max_travel_minutes: number
}

interface RegisterPayload {
  name: string
  email: string
  password: string
  phone?: string
  homeArea: string
  travelMode: 'train' | 'car' | 'either'
  maxTravelMinutes: number
}

interface ProfilePayload {
  name: string
  phone?: string
  homeArea: string
  travelMode: 'train' | 'car' | 'either'
  maxTravelMinutes: number
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  refreshProfile: () => Promise<void>
  updateProfile: (payload: ProfilePayload) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'fe_token'
const USER_KEY = 'fe_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  })

  const persist = (t: string, u: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(USER_KEY, JSON.stringify(u))
    setToken(t)
    setUser(u)
  }

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Login failed.')
    }
    const data = await res.json()
    persist(data.access_token, data.user)
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: payload.name,
        email: payload.email,
        password: payload.password,
        phone: payload.phone,
        home_area: payload.homeArea,
        travel_mode: payload.travelMode,
        max_travel_minutes: payload.maxTravelMinutes,
      }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Registration failed.')
    }
    const data = await res.json()
    persist(data.access_token, data.user)
  }, [])

  const refreshProfile = useCallback(async () => {
    const activeToken = localStorage.getItem(TOKEN_KEY)
    if (!activeToken) return
    const res = await fetch('/auth/me', {
      headers: { Authorization: `Bearer ${activeToken}` },
    })
    if (!res.ok) {
      throw new Error('Failed to load profile.')
    }
    const profile = await res.json()
    persist(activeToken, profile)
  }, [])

  const updateProfile = useCallback(async (payload: ProfilePayload) => {
    const activeToken = localStorage.getItem(TOKEN_KEY)
    if (!activeToken) {
      throw new Error('Not authenticated.')
    }

    const res = await fetch('/auth/me', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${activeToken}`,
      },
      body: JSON.stringify({
        name: payload.name,
        phone: payload.phone || null,
        home_area: payload.homeArea,
        travel_mode: payload.travelMode,
        max_travel_minutes: payload.maxTravelMinutes,
      }),
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Profile update failed.')
    }

    const profile = await res.json()
    persist(activeToken, profile)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, login, register, refreshProfile, updateProfile, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

export function authFetch(url: string, token: string | null, options: RequestInit = {}) {
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
}
