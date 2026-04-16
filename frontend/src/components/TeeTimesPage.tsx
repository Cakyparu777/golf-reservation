import { useState, useEffect } from 'react'
import { Search, Bell, User, MapPin, Star, Lock } from 'lucide-react'
import ConfirmModal from './ConfirmModal'
import { useAuth } from '../context/AuthContext'

export interface CourseData {
  id: number
  name: string
  location: string
  rating: number | null
  amenities: string[]
  next_available: string | null
  min_price: number | null
}

const FILTERS = ['All Courses', 'Championship', 'Links', 'Private']

const COURSE_IMAGES: Record<number, string> = {
  1: 'https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?w=400&q=80',
  2: 'https://images.unsplash.com/photo-1535131749006-b7f58c99034b?w=400&q=80',
  3: 'https://images.unsplash.com/photo-1508193638397-1c4234db14d8?w=400&q=80',
  4: 'https://images.unsplash.com/photo-1592919505780-303950717480?w=400&q=80',
  5: 'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=400&q=80',
}

function formatDate(iso: string | null): string {
  if (!iso) return 'N/A'
  const d = new Date(iso)
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)

  const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  if (d.toDateString() === now.toDateString()) return `Today, ${time}`
  if (d.toDateString() === tomorrow.toDateString()) return `Tomorrow, ${time}`
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) + ` · ${time}`
}

export default function TeeTimesPage() {
  const { token } = useAuth()
  const [activeFilter, setActiveFilter] = useState('All Courses')
  const [courses, setCourses] = useState<CourseData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCourse, setSelectedCourse] = useState<CourseData | null>(null)

  useEffect(() => {
    fetch('/api/courses', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then(setCourses)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token])

  return (
    <div className="min-h-full">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-100">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="pl-9 pr-4 py-2 text-sm bg-gray-100 rounded-xl outline-none w-56 placeholder-gray-400"
            placeholder="Search courses..."
          />
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

      <div className="px-8 py-6">
        <p className="text-xs font-bold text-[#c8922a] uppercase tracking-widest mb-1">Curated Selection</p>
        <h1 className="text-3xl font-extrabold text-[#1a3d2b] mb-2">Recommended Fairways</h1>
        <div className="flex items-start justify-between gap-4">
          <p className="text-sm text-gray-500 max-w-xs">
            Elite choices for your next round, hand-picked based on your play style and current conditions.
          </p>
          <div className="flex gap-2 shrink-0 flex-wrap">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  activeFilter === f
                    ? 'bg-[#1a3d2b] text-white'
                    : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-3 gap-4 mt-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-2xl overflow-hidden shadow-sm animate-pulse">
                <div className="h-40 bg-gray-200" />
                <div className="p-4 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                  <div className="h-3 bg-gray-100 rounded w-1/2" />
                  <div className="h-3 bg-gray-100 rounded w-3/4" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4 mt-6">
            {courses.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                image={COURSE_IMAGES[course.id] || COURSE_IMAGES[1]}
                onSelect={setSelectedCourse}
                formatDate={formatDate}
              />
            ))}

            {/* Special Invitation Card */}
            <div className="bg-[#1a3d2b] rounded-2xl p-5 flex flex-col justify-between text-white relative overflow-hidden">
              <div
                className="absolute inset-0 opacity-20 bg-cover bg-center"
                style={{ backgroundImage: `url('${COURSE_IMAGES[1]}')` }}
              />
              <div className="relative">
                <span className="bg-[#c8922a] text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full">
                  Special Invitation
                </span>
                <h3 className="text-xl font-bold mt-3 leading-snug">Marble Falls Invitational</h3>
                <p className="text-xs text-white/70 mt-2 leading-relaxed">
                  Gain access to the year's most anticipated private tournament layout. Limited slots available for Elite Members only.
                </p>
              </div>
              <div className="relative mt-4">
                <div className="flex items-center gap-1 mb-3">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-6 h-6 rounded-full bg-gray-400 border-2 border-[#1a3d2b]"
                      style={{ marginLeft: i > 0 ? '-6px' : 0 }}
                    />
                  ))}
                  <span className="text-xs text-white/70 ml-2">+42 Elite Members</span>
                </div>
                <button className="w-full bg-[#c8922a] text-white rounded-full py-2 text-sm font-semibold hover:bg-[#d4a645] transition-colors">
                  Inquire for Entry
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Bottom CTA */}
        <div className="mt-6 bg-white rounded-2xl p-5 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#1a3d2b] flex items-center justify-center shrink-0">
              <Star size={16} color="white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Looking for something specific?</p>
              <p className="text-xs text-gray-500">
                Tell me your preferred difficulty, weather conditions, or travel time.
              </p>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button className="border border-gray-300 text-sm font-medium px-4 py-2 rounded-full hover:bg-gray-50 transition-colors">
              Ask Assistant
            </button>
            <button className="border border-gray-300 text-sm font-medium px-4 py-2 rounded-full hover:bg-gray-50 transition-colors">
              View Calendar
            </button>
          </div>
        </div>
      </div>

      {selectedCourse && (
        <ConfirmModal
          course={selectedCourse}
          image={COURSE_IMAGES[selectedCourse.id] || COURSE_IMAGES[1]}
          onClose={() => setSelectedCourse(null)}
        />
      )}
    </div>
  )
}

function CourseCard({
  course,
  image,
  onSelect,
  formatDate,
}: {
  course: CourseData
  image: string
  onSelect: (c: CourseData) => void
  formatDate: (s: string | null) => string
}) {
  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      <div className="relative h-40">
        <img src={image} alt={course.name} className="w-full h-full object-cover" />
        {course.rating && (
          <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-full px-2 py-0.5 flex items-center gap-1">
            <Star size={10} fill="#c8922a" color="#c8922a" />
            <span className="text-xs font-bold text-gray-800">{course.rating}</span>
          </div>
        )}
        {course.amenities.includes('caddie_service') && (
          <div className="absolute top-2 left-2 bg-[#c8922a] text-white text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full flex items-center gap-1">
            <Lock size={8} />
            Member Exclusive
          </div>
        )}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-gray-900">{course.name}</h3>
            <p className="text-xs text-gray-500 flex items-center gap-0.5 mt-0.5">
              <MapPin size={10} />
              {course.location}
            </p>
          </div>
          {course.min_price && (
            <span className="text-xs text-gray-400 font-medium shrink-0">
              from ${course.min_price.toFixed(0)}
            </span>
          )}
        </div>
        <div className="mt-3 flex items-end justify-between">
          <div>
            <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide">Next Available</p>
            <p className="text-sm font-bold text-gray-900">{formatDate(course.next_available)}</p>
          </div>
          <button
            onClick={() => onSelect(course)}
            className="bg-[#1a3d2b] text-white text-xs font-semibold px-4 py-1.5 rounded-full hover:bg-[#1e4d33] transition-colors"
          >
            Select
          </button>
        </div>
      </div>
    </div>
  )
}
