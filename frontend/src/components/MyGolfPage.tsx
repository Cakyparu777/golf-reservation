import { useState, useEffect, useCallback } from 'react'
import { Bell, User, Calendar, Clock } from 'lucide-react'
import { useAuth, authFetch } from '../context/AuthContext'

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

  const fetchReservations = useCallback(() => {
    authFetch('/api/reservations', token)
      .then((r) => r.json())
      .then(setReservations)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token])

  useEffect(() => { fetchReservations() }, [fetchReservations])

  async function handleCancel(id: number) {
    await authFetch(`/api/reservations/${id}`, token, { method: 'DELETE' })
    fetchReservations()
  }

  const upcoming = reservations.filter((r) => r.status !== 'CANCELLED')

  return (
    <div className="min-h-full">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-100">
        <div>
          <h1 className="text-xl font-bold text-gray-900">My Reservations</h1>
          <p className="text-xs text-gray-400">THE CLUBHOUSE</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="relative text-gray-500 hover:text-gray-700">
            <Bell size={20} />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-[#c8922a] rounded-full" />
          </button>
          <div className="w-8 h-8 rounded-full bg-[#1a3d2b] flex items-center justify-center">
            <User size={14} color="white" />
          </div>
        </div>
      </div>

      <div className="px-8 py-6 flex gap-6">
        {/* Left: Reservations */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-gray-900">Upcoming Tee Times</h2>
            <span className="text-sm text-gray-500">{upcoming.length} Total Reservations</span>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-2xl p-4 flex items-center gap-4 shadow-sm animate-pulse">
                  <div className="w-20 h-16 rounded-xl bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/3" />
                    <div className="h-3 bg-gray-100 rounded w-1/2" />
                    <div className="h-3 bg-gray-100 rounded w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : upcoming.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 text-center shadow-sm">
              <p className="text-gray-400 text-sm">No upcoming reservations.</p>
              <p className="text-gray-300 text-xs mt-1">Head to Tee Times to book your next round.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {upcoming.map((r) => (
                <ReservationCard key={r.id} reservation={r} onCancel={handleCancel} />
              ))}
            </div>
          )}
        </div>

        {/* Right: Sidebar widgets */}
        <div className="w-64 shrink-0 space-y-4">
          {/* Promo card */}
          <div className="bg-[#1a3d2b] rounded-2xl p-5 text-white relative overflow-hidden">
            <div className="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_top_right,_white,_transparent)]" />
            <span className="bg-[#c8922a] text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full">
              Elite Perk
            </span>
            <h3 className="text-base font-bold mt-3 leading-snug">Member Pro-Shop Exclusive</h3>
            <p className="text-xs text-white/70 mt-1.5 leading-relaxed">
              Enjoy 25% off all premium equipment and apparel this weekend only.
            </p>
            <button className="mt-4 w-full bg-white text-[#1a3d2b] rounded-full py-2 text-sm font-bold hover:bg-gray-100 transition-colors">
              Redeem Coupon
            </button>
          </div>

          {/* Progress */}
          <div className="bg-white rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-1.5 mb-3">
              <span className="text-[#c8922a]">★</span>
              <h3 className="text-sm font-bold text-gray-900">Elite Status Progress</h3>
            </div>
            <div className="flex items-center justify-between text-xs text-gray-600 mb-1.5">
              <span>Rounds to Platinum</span>
              <span className="font-bold">{upcoming.length} / 15</span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#c8922a] rounded-full transition-all"
                style={{ width: `${Math.min((upcoming.length / 15) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-2 leading-relaxed">
              {Math.max(15 - upcoming.length, 0)} more rounds to unlock early booking benefits.
            </p>
          </div>

          {/* User info */}
          <div className="bg-white rounded-2xl p-4 shadow-sm flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#1a3d2b] flex items-center justify-center text-white text-xs font-bold shrink-0">
              {user?.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">{user?.name}</p>
              <p className="text-xs text-gray-500">Elite Member</p>
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
}: {
  reservation: Reservation
  onCancel: (id: number) => void
}) {
  const isConfirmed = r.status === 'CONFIRMED'
  const d = new Date(r.tee_datetime)
  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  const image = COURSE_IMAGES[r.course_name] || FALLBACK_IMAGE

  return (
    <div className="bg-white rounded-2xl p-4 flex items-center gap-4 shadow-sm">
      <img src={image} alt={r.course_name} className="w-20 h-16 rounded-xl object-cover shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${
              isConfirmed ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
            }`}
          >
            {r.status}
          </span>
        </div>
        <p className="text-sm font-bold text-gray-900 truncate">{r.course_name}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Calendar size={11} /> {dateStr}
          </span>
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Clock size={11} /> {timeStr}
          </span>
        </div>
        <div className="flex items-center gap-1 mt-1.5">
          {Array.from({ length: r.num_players }).map((_, i) => (
            <div
              key={i}
              className="w-5 h-5 rounded-full bg-gray-300 border-2 border-white"
              style={{ marginLeft: i > 0 ? '-4px' : 0 }}
            />
          ))}
          {r.num_players > 1 && (
            <span className="text-[10px] text-gray-500 ml-1">+{r.num_players - 1}</span>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-1.5 shrink-0">
        <button className="border border-gray-300 text-xs font-semibold px-4 py-1.5 rounded-full hover:bg-gray-50 transition-colors">
          Details
        </button>
        <button
          onClick={() => onCancel(r.id)}
          className="text-xs text-gray-400 hover:text-red-500 transition-colors text-center"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
