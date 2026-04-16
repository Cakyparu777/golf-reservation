import { useState, useEffect } from 'react'
import { X, Calendar, Clock, Users, Flag, Award, MapPin, CheckCircle, SunMedium, CloudSun, CloudRain, Loader2 } from 'lucide-react'
import { useAuth, authFetch } from '../context/AuthContext'
import type { CourseData } from './TeeTimesPage'
import { formatJPY } from '../lib/currency'
import { expectJson } from '../lib/api'
import { fetchWeatherForTeeTime, type WeatherSummary } from '../lib/weather'

interface TeeTime {
  id: number
  tee_datetime: string
  available_slots: number
  price_per_player: number
}

interface Props {
  course: CourseData
  image: string
  onClose: () => void
}

export default function ConfirmModal({ course, image, onClose }: Props) {
  const { token } = useAuth()
  const [teeTimes, setTeeTimes] = useState<TeeTime[]>([])
  const [selected, setSelected] = useState<TeeTime | null>(null)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [numPlayers, setNumPlayers] = useState(1)
  const [loading, setLoading] = useState(false)
  const [confirmed, setConfirmed] = useState<{ confirmation_number: string; total_price: number } | null>(null)
  const [error, setError] = useState('')
  const [weather, setWeather] = useState<WeatherSummary | null>(null)

  useEffect(() => {
    let cancelled = false
    setError('')
    fetch(`/api/tee-times?course_id=${course.id}&num_players=${numPlayers}&limit=100`)
      .then((r) => expectJson<TeeTime[]>(r, 'Failed to load tee times.'))
      .then((data: TeeTime[]) => {
        if (cancelled) return
        const nextTeeTimes = Array.isArray(data) ? data : []
        setTeeTimes(nextTeeTimes)
        setSelectedDate((currentDate) => {
          const hasCurrentDate = currentDate && nextTeeTimes.some((tt) => teeDateKey(tt.tee_datetime) === currentDate)
          return hasCurrentDate ? currentDate : (nextTeeTimes[0] ? teeDateKey(nextTeeTimes[0].tee_datetime) : null)
        })
        setSelected((current) => nextTeeTimes.find((tt) => tt.id === current?.id) || nextTeeTimes[0] || null)
        if (nextTeeTimes.length === 0) {
          setError('No tee times are available for that party size right now.')
        }
      })
      .catch((err) => {
        if (cancelled) return
        setTeeTimes([])
        setSelected(null)
        setError(err instanceof Error ? err.message : 'Failed to load tee times.')
      })

    return () => {
      cancelled = true
    }
  }, [course.id, numPlayers])

  useEffect(() => {
    if (!selectedDate) {
      setSelected(teeTimes[0] || null)
      return
    }

    const matchingTimes = teeTimes.filter((tt) => teeDateKey(tt.tee_datetime) === selectedDate)
    if (matchingTimes.length === 0) {
      setSelected(null)
      return
    }

    setSelected((current) => matchingTimes.find((tt) => tt.id === current?.id) || matchingTimes[0])
  }, [selectedDate, teeTimes])

  useEffect(() => {
    if (!selected) {
      setWeather(null)
      return
    }

    let cancelled = false
    setWeather(null)

    fetchWeatherForTeeTime(course.name, selected.tee_datetime)
      .then((data) => {
        if (!cancelled) setWeather(data)
      })
      .catch(() => {
        if (!cancelled) setWeather(null)
      })

    return () => {
      cancelled = true
    }
  }, [course.name, selected])

  function formatDateTime(iso: string) {
    const d = new Date(iso)
    const date = d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
    const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    return { date, time }
  }

  function formatDateLabel(dateKey: string) {
    const d = new Date(`${dateKey}T00:00:00`)
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }

  async function handleConfirm() {
    if (!selected) return
    setError('')
    setLoading(true)
    try {
      const res = await authFetch('/api/reservations', token, {
        method: 'POST',
        body: JSON.stringify({ tee_time_id: selected.id, num_players: numPlayers }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Booking failed.')
      }
      const data = await res.json()
      setConfirmed({ confirmation_number: data.confirmation_number, total_price: data.total_price })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Booking failed.')
    } finally {
      setLoading(false)
    }
  }

  const dt = selected ? formatDateTime(selected.tee_datetime) : null
  const total = selected ? selected.price_per_player * numPlayers : 0
  const availableDates = Array.from(new Set(teeTimes.map((tt) => teeDateKey(tt.tee_datetime))))
  const minAvailableDate = availableDates[0]
  const maxAvailableDate = availableDates[availableDates.length - 1]
  const visibleTeeTimes = selectedDate
    ? teeTimes.filter((tt) => teeDateKey(tt.tee_datetime) === selectedDate)
    : teeTimes
  const WeatherIcon =
    weather?.assessment === 'good'
      ? SunMedium
      : weather?.assessment === 'bad'
        ? CloudRain
        : CloudSun
  const weatherTone =
    weather?.assessment === 'good'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : weather?.assessment === 'bad'
        ? 'bg-rose-50 text-rose-700 border-rose-200'
        : 'bg-amber-50 text-amber-700 border-amber-200'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 backdrop-blur-md bg-green-950/40 animate-fadeIn">
      <div className="bg-white rounded-[2rem] overflow-hidden flex flex-col md:flex-row max-w-4xl w-full max-h-[90vh] shadow-elevated animate-scaleIn">
        {/* Left: Course Image (hidden on very small screens) */}
        <div className="w-full h-48 md:h-auto md:w-80 relative shrink-0 overflow-hidden">
          <img src={image} alt={course.name} className="w-full h-full object-cover img-zoom" />
          <div className="absolute inset-0 bg-gradient-to-t from-green-950/80 via-green-900/40 to-transparent" />
          <div className="absolute bottom-6 left-6 right-6 text-white text-left">
            <p className="text-[10px] uppercase tracking-[.2em] text-gold-300 font-bold mb-1.5 animate-slideUp stagger-1">
              Featured Destination
            </p>
            <h3 className="text-xl md:text-2xl font-black leading-tight animate-slideUp stagger-2">{course.name}</h3>
            <p className="text-sm text-white/80 flex items-center gap-1 mt-2 animate-slideUp stagger-3">
              <MapPin size={12} /> {course.location}
            </p>
          </div>
        </div>

        {/* Right: Booking Details */}
        <div className="flex-1 p-6 md:p-8 flex flex-col overflow-y-auto no-scrollbar relative min-h-[400px]">
          <div className="flex items-start justify-between mb-2">
            <div className="animate-slideUp stagger-1">
              <h2 className="text-2xl font-extrabold text-green-900">
                {confirmed ? "You're on the fairway!" : 'Confirm Booking'}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {confirmed ? `Confirmation # ${confirmed.confirmation_number}` : 'Review your elite booking details below.'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200 hover:text-gray-900 transition-colors shrink-0"
            >
              <X size={16} />
            </button>
          </div>

          {confirmed ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-10 animate-scaleIn stagger-2 relative">
              <div className="absolute inset-0 overflow-hidden pointer-events-none">
                {[...Array(12)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute w-2 h-2 rounded-sm bg-gold-400"
                    style={{
                      left: `${50 + (Math.random() * 40 - 20)}%`,
                      top: '50%',
                      animation: `confettiDrop 1.5s cubic-bezier(.22,1,.36,1) forwards`,
                      animationDelay: `${Math.random() * 200}ms`,
                    }}
                  />
                ))}
              </div>
              <div className="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mb-6 animate-bounceIn">
                <CheckCircle size={40} className="text-green-600" />
              </div>
              <p className="text-2xl font-black text-green-900 mt-2 animate-slideUp stagger-3">{formatJPY(confirmed.total_price)}</p>
              <p className="text-sm text-gray-500 mt-1 animate-slideUp stagger-4">Total amount charged to your card</p>
              <button
                onClick={onClose}
                className="mt-8 bg-gradient-to-r from-green-900 to-green-800 text-white px-10 py-3 rounded-full text-sm font-bold hover:shadow-glow transition-all duration-300 animate-slideUp stagger-5"
              >
                Return to Clubhouse
              </button>
            </div>
          ) : (
            <div className="animate-slideUp stagger-2 flex-1">
              {/* Date selector */}
              {availableDates.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">Select Date</p>
                  <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-soft">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-gold-50 border border-gold-100 flex items-center justify-center shrink-0">
                        <Calendar size={16} className="text-gold-600" />
                      </div>
                      <div className="flex-1">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-1">Booking Date</p>
                        <input
                          type="date"
                          value={selectedDate ?? ''}
                          min={minAvailableDate}
                          max={maxAvailableDate}
                          onChange={(event) => setSelectedDate(event.target.value)}
                          className="w-full bg-transparent text-sm font-bold text-gray-900 outline-none"
                        />
                      </div>
                    </div>
                    <p className="mt-3 text-xs text-gray-500">
                      Available booking window: {formatDateLabel(minAvailableDate)} to {formatDateLabel(maxAvailableDate)}
                    </p>
                  </div>
                </div>
              )}

              {/* Tee time selector */}
              {visibleTeeTimes.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">Select Tee Time</p>
                  <div className="flex gap-2.5 flex-wrap">
                    {visibleTeeTimes.map((tt) => {
                      const d = new Date(tt.tee_datetime)
                      const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                      const isSelected = selected?.id === tt.id
                      return (
                        <button
                          key={tt.id}
                          onClick={() => setSelected(tt)}
                          className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 border ${
                            isSelected
                              ? 'bg-green-900 border-green-900 text-white shadow-soft animate-ringPulse'
                              : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50 hover:-translate-y-0.5 relative z-10'
                          }`}
                        >
                          <span className={isSelected ? 'text-green-200' : 'text-gray-700'}>{timeStr}</span>
                          <span className={`ml-2 text-[10px] font-bold ${isSelected ? 'text-green-100' : 'text-gray-400'}`}>
                            {tt.available_slots} spots
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {dt && (
                <div className="grid grid-cols-2 gap-x-6 gap-y-5 mt-8 bg-surface-muted border border-gray-100 rounded-2xl p-5">
                  <DateDetail
                    value={selectedDate ?? ''}
                    min={minAvailableDate}
                    max={maxAvailableDate}
                    onChange={(value) => setSelectedDate(value)}
                  />
                  <SelectDetail
                    icon={Clock}
                    label="Time"
                    value={selected ? String(selected.id) : ''}
                    onChange={(value) => {
                      const next = visibleTeeTimes.find((tt) => String(tt.id) === value)
                      if (next) setSelected(next)
                    }}
                    options={visibleTeeTimes.map((tt) => ({
                      value: String(tt.id),
                      label: new Date(tt.tee_datetime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                    }))}
                  />
                  <div>
                    <p className="text-[10px] uppercase text-gray-400 font-bold tracking-widest">Party Size</p>
                    <div className="flex items-center gap-2 mt-1.5 focus-within:ring-2 focus-within:ring-green-900/10 rounded-lg pr-2 transition-shadow">
                      <div className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center shrink-0">
                        <Users size={12} className="text-gray-500" />
                      </div>
                      <select
                        value={numPlayers}
                        onChange={(e) => setNumPlayers(Number(e.target.value))}
                        className="text-sm font-bold text-gray-900 bg-transparent outline-none w-full"
                      >
                        {[1, 2, 3, 4].map((n) => (
                          <option key={n} value={n}>
                            {n} {n === 1 ? 'Player' : 'Players'}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <Detail icon={Flag} label="Tee Box" value="Championship" />
                </div>
              )}

              {weather && (
                <div className={`mt-4 rounded-2xl border px-5 py-4 flex items-start gap-3 animate-slideDown ${weatherTone}`}>
                  <WeatherIcon size={18} className="shrink-0 animate-pulseSoft mt-0.5" />
                  <div>
                    <p className="text-sm font-bold">
                      {weather.assessment === 'good'
                        ? 'Optimal Conditions'
                        : weather.assessment === 'bad'
                          ? 'Challenging Weather'
                          : 'Playable with caution'}
                    </p>
                    <p className="text-xs mt-1 leading-relaxed opacity-90">{weather.message}</p>
                  </div>
                </div>
              )}

              {/* Add-on */}
              <div className="mt-4 bg-gradient-to-r from-gray-50 to-white border border-gray-100 rounded-2xl p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center shrink-0 shadow-soft">
                  <Award size={18} color="white" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-green-900">Premium Caddie Service</p>
                  <p className="text-xs text-gray-500 mt-0.5">Complimentary for Elite tier members.</p>
                </div>
                <span className="text-[10px] font-black text-gold-500 border border-gold-500/30 bg-gold-50 px-2.5 py-1 rounded-full shrink-0">
                  INCLUDED
                </span>
              </div>

              {error && (
                <div className="mt-4 text-sm font-medium text-rose-700 bg-rose-50 border border-rose-200 px-4 py-3 rounded-xl animate-slideDown">
                  {error}
                </div>
              )}

              {!error && selectedDate && visibleTeeTimes.length === 0 && (
                <div className="mt-4 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 px-4 py-3 rounded-xl animate-slideDown">
                  No tee times are available on {formatDateLabel(selectedDate)} for {numPlayers} {numPlayers === 1 ? 'player' : 'players'}. Try another date or party size.
                </div>
              )}

              {/* Footer */}
              <div className="mt-8">
                <div className="flex items-end justify-between mb-4">
                  <p className="text-sm font-medium text-gray-500">Total Booking Fee</p>
                  <p className="text-3xl font-black text-green-900 tracking-tight">{formatJPY(total)}</p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    disabled={loading}
                    className="px-6 py-3.5 rounded-2xl text-sm font-bold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={loading || !selected}
                    className="flex-1 bg-gradient-to-r from-green-900 to-green-800 text-white rounded-2xl py-3.5 text-sm font-bold hover:shadow-glow transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-60 disabled:hover:shadow-none"
                  >
                    {loading ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        Processing…
                      </>
                    ) : (
                      'Confirm Booking →'
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function teeDateKey(iso: string) {
  return iso.slice(0, 10)
}

function Detail({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase text-gray-400 font-bold tracking-widest mb-1.5">{label}</p>
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center shrink-0">
          <Icon size={12} className="text-gray-500" />
        </div>
        <p className="text-sm font-bold text-gray-900 truncate">{value}</p>
      </div>
    </div>
  )
}

function DateDetail({
  value,
  min,
  max,
  onChange,
}: {
  value: string
  min?: string
  max?: string
  onChange: (value: string) => void
}) {
  return (
    <div>
      <p className="text-[10px] uppercase text-gray-400 font-bold tracking-widest mb-1.5">Date</p>
      <div className="flex items-center gap-2 mt-1.5 focus-within:ring-2 focus-within:ring-green-900/10 rounded-lg pr-2 transition-shadow">
        <div className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center shrink-0">
          <Calendar size={12} className="text-gray-500" />
        </div>
        <input
          type="date"
          value={value}
          min={min}
          max={max}
          onChange={(event) => onChange(event.target.value)}
          className="text-sm font-bold text-gray-900 bg-transparent outline-none w-full"
        />
      </div>
    </div>
  )
}

function SelectDetail({
  icon: Icon,
  label,
  value,
  onChange,
  options,
}: {
  icon: React.ElementType
  label: string
  value: string
  onChange: (value: string) => void
  options: Array<{ value: string; label: string }>
}) {
  return (
    <div>
      <p className="text-[10px] uppercase text-gray-400 font-bold tracking-widest mb-1.5">{label}</p>
      <div className="flex items-center gap-2 mt-1.5 focus-within:ring-2 focus-within:ring-green-900/10 rounded-lg pr-2 transition-shadow">
        <div className="w-7 h-7 rounded-lg bg-white border border-gray-200 flex items-center justify-center shrink-0">
          <Icon size={12} className="text-gray-500" />
        </div>
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="text-sm font-bold text-gray-900 bg-transparent outline-none w-full"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
