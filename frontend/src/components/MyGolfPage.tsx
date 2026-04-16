import { useState, useEffect, useCallback } from 'react'
import { Bell, User, Calendar, Clock, SearchX } from 'lucide-react'
import { useAuth, authFetch } from '../context/AuthContext'
import { expectJson, readErrorMessage } from '../lib/api'
import { formatJPY } from '../lib/currency'

interface Reservation {
  id: number
  course_name: string
  tee_datetime: string
  num_players: number
  total_price: number
  status: string
  confirmation_number: string | null
}

const COURSE_IMAGES: Record<string, string> = {
  'Wakasu Golf Links': 'https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?w=200&q=80',
  'Tokyo Kokusai Golf Club': 'https://images.unsplash.com/photo-1535131749006-b7f58c99034b?w=200&q=80',
  'Sakuragaoka Country Club': 'https://images.unsplash.com/photo-1508193638397-1c4234db14d8?w=200&q=80',
  'Tama Hills Golf Course': 'https://images.unsplash.com/photo-1592919505780-303950717480?w=200&q=80',
  'Sodegaura Country Club': 'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=200&q=80',
}

const FALLBACK_IMAGE = 'https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?w=200&q=80'

export default function MyGolfPage() {
  const { token, user } = useAuth()
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchReservations = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const response = await authFetch('/api/reservations', token)
      const data = await expectJson<Reservation[]>(response, 'Failed to load reservations.')
      setReservations(Array.isArray(data) ? data : [])
    } catch (err) {
      setReservations([])
      setError(err instanceof Error ? err.message : 'Failed to load reservations.')
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchReservations()
  }, [fetchReservations])

  async function handleCancel(id: number) {
    setError('')
    try {
      const response = await authFetch(`/api/reservations/${id}`, token, { method: 'DELETE' })
      if (!response.ok) {
        throw new Error(await readErrorMessage(response, 'Failed to cancel reservation.'))
      }
      await fetchReservations()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel reservation.')
    }
  }

  const upcoming = reservations.filter((r) => r.status !== 'CANCELLED')
  const progressPercent = Math.min((upcoming.length / 15) * 100, 100)

  return (
    <div className="min-h-full animate-fadeIn pb-24 md:pb-6">
      <div className="flex items-center justify-between px-4 md:px-8 py-4 bg-white/80 backdrop-blur-lg border-b border-gray-100 sticky top-0 z-30">
        <div className="animate-slideInLeft">
          <h1 className="text-xl font-extrabold text-green-900 tracking-tight">My Reservations</h1>
          <p className="text-[10px] uppercase font-bold text-gold-500 tracking-widest mt-0.5">The Clubhouse</p>
        </div>
        <div className="flex items-center gap-3 animate-slideInRight">
          <button className="relative text-gray-500 hover:text-green-900 transition-colors p-1">
            <Bell size={20} />
            <span className="absolute top-1 right-1 w-2 h-2 bg-gold-400 rounded-full border border-white" />
          </button>
        </div>
      </div>

      <div className="px-4 md:px-8 py-6 flex flex-col xl:flex-row gap-6">
        <div className="flex-1 max-w-4xl animate-slideUp">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-bold text-gray-900">Upcoming Rounds</h2>
            <div className="bg-white border border-gray-200 px-3 py-1 rounded-full text-xs font-bold text-gray-600 shadow-sm">
              {upcoming.length} Total
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-[1.25rem] p-4 flex flex-col sm:flex-row items-center gap-4 shadow-soft border border-gray-100 animate-pulse">
                  <div className="w-full sm:w-28 h-32 sm:h-24 rounded-xl bg-gray-100 shrink-0" />
                  <div className="flex-1 w-full space-y-2.5 py-1">
                    <div className="h-5 bg-gray-100 rounded-md w-1/2" />
                    <div className="h-3 bg-gray-50 rounded w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : upcoming.length === 0 ? (
            <div className="bg-white/50 border border-dashed border-gray-300 rounded-[2rem] p-12 text-center flex flex-col items-center justify-center animate-scaleIn">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-gray-400">
                <SearchX size={24} />
              </div>
              <h3 className="text-lg font-bold text-gray-900">No upcoming rounds</h3>
              <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
                Your schedule is clear. Check the Tee Times view or ask your assistant to find the perfect slot.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {upcoming.map((r, i) => (
                <ReservationCard key={r.id} reservation={r} onCancel={handleCancel} index={i} />
              ))}
            </div>
          )}
        </div>

        <div className="w-full xl:w-80 shrink-0 flex flex-col gap-5 xl:sticky xl:top-24 h-max animate-slideUp stagger-3">
          <div className="bg-white rounded-[1.5rem] p-5 shadow-card border border-gray-100/50 flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center text-white text-xl font-bold shadow-soft mb-3 relative">
              {user?.name.charAt(0).toUpperCase()}
              <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-gold-400 rounded-full border-2 border-white flex items-center justify-center">
                <span className="text-white text-[8px] font-black">★</span>
              </div>
            </div>
            <h2 className="text-lg font-extrabold text-gray-900">{user?.name}</h2>
            <p className="text-xs font-semibold text-gold-500 uppercase tracking-widest mt-0.5">Elite Member</p>
          </div>

          <div className="bg-white rounded-[1.5rem] p-6 shadow-soft border border-gray-100 overflow-hidden relative group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gold-500/5 rounded-bl-[100%] transition-transform group-hover:scale-110" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gold-50 text-gold-500 flex items-center justify-center">
                  <span className="text-sm">★</span>
                </div>
                <h3 className="text-sm font-bold text-gray-900">Status Progress</h3>
              </div>
              <div className="flex items-end justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Rounds</span>
                <span className="text-sm font-black text-green-900">{upcoming.length} <span className="text-gray-400">/ 15</span></span>
              </div>
              <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-gold-500 to-gold-400 rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-3 font-medium">
                {Math.max(15 - upcoming.length, 0)} rounds remaining to unlock Platinum priority booking.
              </p>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-900 to-green-950 rounded-[1.5rem] p-6 text-white relative overflow-hidden card-hover">
            <div className="absolute inset-0 opacity-20 bg-[radial-gradient(circle_at_top_right,_white,_transparent)]" />
            <div className="relative">
              <span className="bg-gold-500 text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full inline-block mb-3">
                Pro-Shop Exclusive
              </span>
              <h3 className="text-lg font-black leading-tight mb-2">Elite Apparel Event</h3>
              <p className="text-xs text-white/70 leading-relaxed mb-5">
                Enjoy 25% off all premium equipment and apparel this weekend only.
              </p>
              <button className="w-full bg-white text-green-900 rounded-xl py-2.5 text-sm font-bold hover:shadow-glow transition-all active:scale-[.98]">
                Redeem Coupon
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ReservationCard({
  reservation: r,
  onCancel,
  index,
}: {
  reservation: Reservation
  onCancel: (id: number) => void
  index: number
}) {
  const isConfirmed = r.status === 'CONFIRMED'
  const d = new Date(r.tee_datetime)
  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  const image = COURSE_IMAGES[r.course_name] || FALLBACK_IMAGE

  return (
    <div className={`bg-white rounded-[1.25rem] p-4 flex flex-col sm:flex-row items-center gap-5 shadow-soft hover:shadow-card transition-shadow border border-gray-100 group animate-slideUp stagger-${(index % 5) + 1}`}>
      <div className="w-full sm:w-32 h-32 sm:h-24 shrink-0 overflow-hidden rounded-xl relative">
        <img src={image} alt={r.course_name} className="w-full h-full object-cover img-zoom" />
        <div className="absolute top-2 left-2">
          <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-md backdrop-blur-md border ${
            isConfirmed ? 'bg-emerald-500/90 text-white border-emerald-500/20' : 'bg-amber-500/90 text-white border-amber-500/20'
          }`}>
            {r.status}
          </span>
        </div>
      </div>

      <div className="flex-1 min-w-0 w-full flex flex-col justify-center">
        <h3 className="text-base font-extrabold text-gray-900 truncate">{r.course_name}</h3>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
            <Calendar size={12} className="text-green-900" /> {dateStr}
          </div>
          <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
            <Clock size={12} className="text-green-900" /> {timeStr}
          </div>
          <div className="flex items-center text-xs font-semibold text-gray-600 bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
            <User size={12} className="text-green-900 mr-1.5" />
            {r.num_players} {r.num_players === 1 ? 'Player' : 'Players'}
          </div>
        </div>
      </div>

      <div className="w-full sm:w-auto flex sm:flex-col items-center justify-between sm:justify-center gap-2 sm:pl-4 sm:border-l border-gray-100 shrink-0">
        <div className="text-left sm:text-right w-full sm:mb-2">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Total</p>
          <p className="text-sm font-black text-green-900">{formatJPY(r.total_price)}</p>
        </div>
        <button
          onClick={() => {
            if (confirm(`Are you sure you want to cancel your reservation for ${r.course_name}?`)) {
              onCancel(r.id)
            }
          }}
          className="text-xs font-bold text-gray-400 hover:text-white hover:bg-rose-500 hover:border-rose-500 transition-all border border-gray-200 px-4 py-2 rounded-lg flex items-center justify-center gap-1.5"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
