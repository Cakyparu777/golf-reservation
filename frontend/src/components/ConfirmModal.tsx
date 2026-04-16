import { useState, useEffect } from 'react'
import { X, Calendar, Clock, Users, Flag, Award, MapPin, CheckCircle, SunMedium, CloudSun, CloudRain } from 'lucide-react'
import { useAuth, authFetch } from '../context/AuthContext'
import type { CourseData } from './TeeTimesPage'
import { formatJPY } from '../lib/currency'
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
  const [numPlayers, setNumPlayers] = useState(1)
  const [loading, setLoading] = useState(false)
  const [confirmed, setConfirmed] = useState<{ confirmation_number: string; total_price: number } | null>(null)
  const [error, setError] = useState('')
  const [weather, setWeather] = useState<WeatherSummary | null>(null)

  useEffect(() => {
    fetch(`/api/tee-times?course_id=${course.id}&num_players=1&limit=10`)
      .then((r) => r.json())
      .then((data: TeeTime[]) => {
        setTeeTimes(data)
        if (data.length > 0) setSelected(data[0])
      })
      .catch(console.error)
  }, [course.id])

  useEffect(() => {
    if (!selected) {
      setWeather(null)
      return
    }

    let cancelled = false

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
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl overflow-hidden flex max-w-3xl w-full shadow-2xl">
        {/* Left: Course Image */}
        <div className="w-72 relative shrink-0">
          <img src={image} alt={course.name} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          <div className="absolute bottom-5 left-5 text-white">
            <p className="text-[10px] uppercase tracking-widest text-white/70 font-semibold mb-1">
              Featured Destination
            </p>
            <h3 className="text-lg font-bold leading-snug">{course.name}</h3>
            <p className="text-xs text-white/80 flex items-center gap-1 mt-0.5">
              <MapPin size={11} /> {course.location}
            </p>
          </div>
        </div>

        {/* Right: Booking Details */}
        <div className="flex-1 p-7 flex flex-col overflow-y-auto max-h-[90vh]">
          <div className="flex items-start justify-between mb-1">
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {confirmed ? 'Booking Confirmed!' : 'Confirm Reservation'}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {confirmed ? `Confirmation # ${confirmed.confirmation_number}` : 'Review your elite booking details below.'}
              </p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
              <X size={20} />
            </button>
          </div>

          {confirmed ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-8">
              <CheckCircle size={56} className="text-[#1a3d2b] mb-4" />
              <p className="text-lg font-bold text-gray-900">You're on the fairway!</p>
              <p className="text-sm text-gray-500 mt-1 mb-2">{course.name}</p>
              <p className="text-2xl font-extrabold text-gray-900 mt-2">{formatJPY(confirmed.total_price)}</p>
              <p className="text-xs text-gray-400 mt-1">Total charged</p>
              <button
                onClick={onClose}
                className="mt-6 bg-[#1a3d2b] text-white px-8 py-2.5 rounded-full text-sm font-semibold hover:bg-[#1e4d33] transition-colors"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              {/* Tee time selector */}
              {teeTimes.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Select Tee Time</p>
                  <div className="flex gap-2 flex-wrap">
                    {teeTimes.slice(0, 6).map((tt) => {
                      const d = new Date(tt.tee_datetime)
                      const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                      const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      return (
                        <button
                          key={tt.id}
                          onClick={() => setSelected(tt)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                            selected?.id === tt.id
                              ? 'bg-[#1a3d2b] text-white border-[#1a3d2b]'
                              : 'bg-white border-gray-200 text-gray-700 hover:border-gray-300'
                          }`}
                        >
                          {dateStr} {timeStr}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {dt && (
                <div className="grid grid-cols-2 gap-4 mt-5">
                  <Detail icon={Calendar} label="Date" value={dt.date} />
                  <Detail icon={Clock} label="Time" value={dt.time} />
                  <div>
                    <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide">Players</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Users size={14} className="text-gray-500" />
                      <select
                        value={numPlayers}
                        onChange={(e) => setNumPlayers(Number(e.target.value))}
                        className="text-sm font-semibold text-gray-900 bg-transparent outline-none"
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

              {weather?.assessment && weather?.message && (
                <div className={`mt-5 rounded-2xl border px-4 py-3 ${weatherTone}`}>
                  <div className="flex items-center gap-2">
                    <WeatherIcon size={16} />
                    <p className="text-sm font-bold">
                      {weather.assessment === 'good'
                        ? 'Good golf weather'
                        : weather.assessment === 'bad'
                          ? 'Challenging golf weather'
                          : 'Playable with caution'}
                    </p>
                  </div>
                  <p className="text-xs mt-1.5 leading-relaxed">{weather.message}</p>
                </div>
              )}

              {/* Add-on */}
              <div className="mt-5 bg-gray-50 rounded-2xl p-4 flex items-start gap-3">
                <div className="w-9 h-9 rounded-full bg-[#1a3d2b] flex items-center justify-center shrink-0">
                  <Award size={16} color="white" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-[#1a3d2b]">Premium Caddie Service</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Dedicated professional guidance included for your foursome.
                  </p>
                </div>
                <span className="text-xs font-bold text-[#c8922a] border border-[#c8922a] px-2 py-0.5 rounded-full shrink-0">
                  GOLD TIER
                </span>
              </div>

              {error && (
                <p className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-xl">{error}</p>
              )}

              {/* Price */}
              <div className="mt-5 flex items-center justify-between border-t border-gray-100 pt-4">
                <p className="text-sm text-gray-500">Total Booking Fee</p>
                <p className="text-2xl font-extrabold text-gray-900">{formatJPY(total)}</p>
              </div>

              <button
                onClick={handleConfirm}
                disabled={loading || !selected}
                className="mt-4 w-full bg-[#1a3d2b] text-white rounded-2xl py-3.5 text-sm font-bold hover:bg-[#1e4d33] transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
              >
                {loading ? 'Processing…' : 'Confirm Booking →'}
              </button>
              <button
                onClick={onClose}
                className="mt-2 text-xs text-gray-400 hover:text-gray-600 transition-colors text-center"
              >
                Cancel and return to Clubhouse
              </button>
            </>
          )}
        </div>
      </div>

      {/* Watermark */}
      <div className="absolute bottom-6 right-8 text-4xl font-black text-white/10 select-none pointer-events-none tracking-widest">
        FAIRWAY ELITE
      </div>
    </div>
  )
}

function Detail({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide">{label}</p>
      <p className="text-sm font-semibold text-gray-900 flex items-center gap-1.5 mt-1">
        <Icon size={14} className="text-gray-500" />
        {value}
      </p>
    </div>
  )
}
