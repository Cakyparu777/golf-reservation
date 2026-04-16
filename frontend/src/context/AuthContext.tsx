import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { supabase } from '../lib/supabase'

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
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'fe_token'
const USER_KEY = 'fe_user'

async function fetchProfile(accessToken: string): Promise<AuthUser> {
  const res = await fetch('/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to load profile.')
  }
  return res.json()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  })

  const clearPersisted = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const persist = useCallback((nextToken: string, nextUser: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, nextToken)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
    setToken(nextToken)
    setUser(nextUser)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      throw new Error('Supabase is not configured for the frontend.')
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error || !data.session) {
      throw new Error(error?.message || 'Login failed.')
    }

    const profile = await fetchProfile(data.session.access_token)
    persist(data.session.access_token, profile)
  }, [persist])

  const register = useCallback(async (payload: RegisterPayload) => {
    if (!supabase) {
      throw new Error('Supabase is not configured for the frontend.')
    }

    const { data, error } = await supabase.auth.signUp({
      email: payload.email,
      password: payload.password,
      options: {
        data: {
          full_name: payload.name,
          phone: payload.phone || null,
        },
      },
    })

    if (error) {
      throw new Error(error.message || 'Registration failed.')
    }

    if (!data.session) {
      throw new Error('Signup succeeded, but no session was returned. Please verify your email and sign in.')
    }

    const res = await fetch('/auth/me', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${data.session.access_token}`,
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
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Registration failed.')
    }

    const profile = await res.json()
    persist(data.session.access_token, profile)
  }, [persist])

  const refreshProfile = useCallback(async () => {
    const activeToken = localStorage.getItem(TOKEN_KEY)
    if (!activeToken) return
    const profile = await fetchProfile(activeToken)
    persist(activeToken, profile)
  }, [persist])

  const updateProfile = useCallback(async (payload: ProfilePayload) => {
    const activeToken = localStorage.getItem(TOKEN_KEY)
    if (!activeToken) {
      throw new Error('Not authenticated.')
    }

    if (supabase) {
      const { error } = await supabase.auth.updateUser({
        data: {
          full_name: payload.name,
          phone: payload.phone || null,
        },
      })
      if (error) {
        throw new Error(error.message || 'Profile update failed.')
      }
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
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Profile update failed.')
    }

    const profile = await res.json()
    persist(activeToken, profile)
  }, [persist])

  const logout = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    clearPersisted()
  }, [clearPersisted])

  useEffect(() => {
    if (!supabase) return

    supabase.auth.getSession().then(({ data }) => {
      const session = data.session
      if (!session) {
        clearPersisted()
        return
      }
      if (session.access_token !== token || !user) {
        fetchProfile(session.access_token)
          .then((profile) => persist(session.access_token, profile))
          .catch(() => clearPersisted())
      }
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        clearPersisted()
        return
      }
      fetchProfile(session.access_token)
        .then((profile) => persist(session.access_token, profile))
        .catch(() => clearPersisted())
    })

    return () => subscription.unsubscribe()
  }, [clearPersisted, persist, token, user])

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
