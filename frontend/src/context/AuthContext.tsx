import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { supabase } from '../lib/supabase'
import { expectJson } from '../lib/api'

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
  authReady: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  refreshProfile: () => Promise<void>
  updateProfile: (payload: ProfilePayload) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function fetchProfile(accessToken: string): Promise<AuthUser> {
  const res = await fetch('/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return expectJson<AuthUser>(res, 'Failed to load profile.')
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [authReady, setAuthReady] = useState(false)

  const clearPersisted = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const persist = useCallback((nextToken: string, nextUser: AuthUser) => {
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

    const profile = await expectJson<AuthUser>(res, 'Registration failed.')
    persist(data.session.access_token, profile)
  }, [persist])

  const refreshProfile = useCallback(async () => {
    if (!token) return
    const profile = await fetchProfile(token)
    persist(token, profile)
  }, [persist, token])

  const updateProfile = useCallback(async (payload: ProfilePayload) => {
    if (!token) {
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
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: payload.name,
        phone: payload.phone || null,
        home_area: payload.homeArea,
        travel_mode: payload.travelMode,
        max_travel_minutes: payload.maxTravelMinutes,
      }),
    })

    const profile = await expectJson<AuthUser>(res, 'Profile update failed.')
    persist(token, profile)
  }, [persist, token])

  const logout = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    clearPersisted()
  }, [clearPersisted])

  useEffect(() => {
    if (!supabase) {
      clearPersisted()
      setAuthReady(true)
      return
    }

    const supabaseClient = supabase

    let active = true

    const hydrate = async () => {
      try {
        const { data } = await supabaseClient.auth.getSession()
        const session = data.session

        if (!active) return

        if (!session) {
          clearPersisted()
          return
        }

        const profile = await fetchProfile(session.access_token)
        if (!active) return
        persist(session.access_token, profile)
      } catch {
        if (!active) return
        clearPersisted()
      } finally {
        if (active) {
          setAuthReady(true)
        }
      }
    }

    hydrate()

    const {
      data: { subscription },
    } = supabaseClient.auth.onAuthStateChange(async (_event, session) => {
      if (!active) return

      if (!session) {
        clearPersisted()
        setAuthReady(true)
        return
      }

      try {
        const profile = await fetchProfile(session.access_token)
        if (!active) return
        persist(session.access_token, profile)
      } catch {
        if (!active) return
        clearPersisted()
      } finally {
        if (active) {
          setAuthReady(true)
        }
      }
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [clearPersisted, persist])

  return (
    <AuthContext.Provider value={{ user, token, authReady, login, register, refreshProfile, updateProfile, logout }}>
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
