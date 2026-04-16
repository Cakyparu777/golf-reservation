import { useState, useEffect } from 'react'
import { Search, MapPin, Star, Lock, SunMedium, CloudSun, CloudRain, Sparkles, ArrowRight } from 'lucide-react'
import ConfirmModal from './ConfirmModal'
import { useAuth } from '../context/AuthContext'
import { formatJPY } from '../lib/currency'
import { expectJson } from '../lib/api'
import { fetchWeatherForTeeTime, type WeatherSummary } from '../lib/weather'
import { fetchRecommendations, type RecommendedTeeTime } from '../lib/recommendations'

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

function tomorrowIsoDate(): string {
  const next = new Date()
  next.setDate(next.getDate() + 1)
  const year = next.getFullYear()
  const month = String(next.getMonth() + 1).padStart(2, '0')
  const day = String(next.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export default function TeeTimesPage() {
  const { token, user } = useAuth()
  const [activeFilter, setActiveFilter] = useState('All Courses')
  const [courses, setCourses] = useState<CourseData[]>([])
  const [weatherByCourseId, setWeatherByCourseId] = useState<Record<number, WeatherSummary | null>>({})
  const [recommendations, setRecommendations] = useState<RecommendedTeeTime[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedCourse, setSelectedCourse] = useState<CourseData | null>(null)
  const [searchFocused, setSearchFocused] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    fetch('/api/courses', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => expectJson<CourseData[]>(r, 'Failed to load courses.'))
      .then((data) => {
        if (cancelled) return
        setCourses(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        if (cancelled) return
        setCourses([])
        setError(err instanceof Error ? err.message : 'Failed to load courses.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    const eligibleCourses = courses.filter((course) => course.next_available)
    if (eligibleCourses.length === 0) return

    let cancelled = false

    Promise.all(
      eligibleCourses.map(async (course) => {
        try {
          const weather = await fetchWeatherForTeeTime(course.name, course.next_available as string)
          return [course.id, weather] as const
        } catch {
          return [course.id, null] as const
        }
      })
    ).then((entries) => {
      if (cancelled) return
      setWeatherByCourseId(Object.fromEntries(entries))
    })

    return () => {
      cancelled = true
    }
  }, [courses])

  useEffect(() => {
    fetchRecommendations({
      date: tomorrowIsoDate(),
      numPlayers: 1,
      preferredTime: 'morning',
      userArea: user?.home_area,
      travelMode: user?.travel_mode,
      maxTravelMinutes: user?.max_travel_minutes,
      maxResults: 3,
    })
      .then((data) => setRecommendations(data.recommended_tee_times))
      .catch(() => setRecommendations([]))
  }, [user])

  return (
    <div className="min-h-full animate-fadeIn">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 md:px-8 py-4 bg-white/80 backdrop-blur-lg border-b border-gray-100 sticky top-0 z-30">
        <div className={`relative transition-all duration-300 ${searchFocused ? 'w-80' : 'w-56'}`}>
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            id="course-search"
            className="pl-9 pr-4 py-2 text-sm bg-gray-50 border border-transparent rounded-xl outline-none w-full placeholder-gray-400 focus:bg-white focus:border-green-900/20 focus:ring-2 focus:ring-green-900/10 transition-all"
            placeholder="Search courses..."
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
          />
        </div>
      </div>

      <div className="px-4 md:px-8 py-6">
        <div className="animate-slideUp">
          <p className="text-xs font-bold text-gold-500 uppercase tracking-[.15em] mb-1">Curated Selection</p>
          <h1 className="text-2xl md:text-3xl font-extrabold text-green-900 mb-2">Recommended Fairways</h1>
        </div>
        <div className="flex flex-col md:flex-row items-start justify-between gap-4 animate-slideUp stagger-1">
          <p className="text-sm text-gray-500 max-w-xs">
            Elite choices for your next round, hand-picked based on your play style and current conditions.
          </p>
          <div className="flex gap-2 shrink-0 flex-wrap">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setActiveFilter(f)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                  activeFilter === f
                    ? 'bg-green-900 text-white shadow-sm'
                    : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="mt-6 bg-white rounded-3xl p-5 shadow-soft border border-gray-100/60 animate-slideUp stagger-2">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={14} className="text-gold-500" />
              <p className="text-xs font-bold text-gold-500 uppercase tracking-[.15em]">Smart Suggestions</p>
            </div>
            <h2 className="text-lg font-extrabold text-green-900">Best Times To Play Next</h2>
            <p className="text-sm text-gray-500 mt-1 mb-4">Weather-aware picks for tomorrow morning.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {recommendations.map((recommendation, i) => (
                <RecommendationCard key={recommendation.tee_time.id} recommendation={recommendation} index={i} />
              ))}
            </div>
          </div>
        )}

        {/* Course Grid */}
        {error && (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-2xl overflow-hidden shadow-soft animate-pulse">
                <div className="h-40 bg-gray-100" />
                <div className="p-4 space-y-2">
                  <div className="h-4 bg-gray-100 rounded w-2/3" />
                  <div className="h-3 bg-gray-50 rounded w-1/2" />
                  <div className="h-3 bg-gray-50 rounded w-3/4" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            {courses.map((course, i) => (
              <CourseCard
                key={course.id}
                course={course}
                image={COURSE_IMAGES[course.id] || COURSE_IMAGES[1]}
                onSelect={setSelectedCourse}
                formatDate={formatDate}
                weather={weatherByCourseId[course.id]}
                index={i}
              />
            ))}

            {/* Special Invitation Card */}
            <div className="bg-gradient-to-br from-green-900 to-green-950 rounded-2xl p-5 flex flex-col justify-between text-white relative overflow-hidden card-hover animate-slideUp stagger-6">
              <div
                className="absolute inset-0 opacity-10 bg-cover bg-center"
                style={{ backgroundImage: `url('${COURSE_IMAGES[1]}')` }}
              />
              <div className="relative">
                <span className="bg-gold-500 text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full">
                  Special Invitation
                </span>
                <h3 className="text-xl font-bold mt-3 leading-snug">Marble Falls Invitational</h3>
                <p className="text-xs text-white/60 mt-2 leading-relaxed">
                  Gain access to the year's most anticipated private tournament layout. Limited slots available for Elite Members only.
                </p>
              </div>
              <div className="relative mt-4">
                <div className="flex items-center gap-1 mb-3">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-6 h-6 rounded-full bg-white/20 border-2 border-green-900"
                      style={{ marginLeft: i > 0 ? '-6px' : 0 }}
                    />
                  ))}
                  <span className="text-xs text-white/50 ml-2">+42 Elite Members</span>
                </div>
                <button className="w-full bg-gradient-to-r from-gold-500 to-gold-400 text-green-950 rounded-xl py-2.5 text-sm font-bold hover:shadow-glow transition-all duration-300">
                  Inquire for Entry
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Bottom CTA */}
        <div className="mt-6 bg-white rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between shadow-soft border border-gray-100/60 gap-4 animate-slideUp">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-900 to-green-700 flex items-center justify-center shrink-0">
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
            <button className="border border-gray-200 text-sm font-medium px-4 py-2 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all flex items-center gap-1.5">
              Ask Assistant <ArrowRight size={13} />
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

function RecommendationCard({ recommendation, index }: { recommendation: RecommendedTeeTime; index: number }) {
  const teeTime = recommendation.tee_time
  const weatherAssessment = recommendation.weather_assessment
  const WeatherIcon =
    weatherAssessment === 'good'
      ? SunMedium
      : weatherAssessment === 'bad'
        ? CloudRain
        : CloudSun

  const weatherTone =
    weatherAssessment === 'good'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : weatherAssessment === 'bad'
        ? 'bg-rose-50 text-rose-700 border-rose-200'
        : 'bg-amber-50 text-amber-700 border-amber-200'

  return (
    <div className={`rounded-2xl border border-gray-100 bg-surface-muted p-4 card-hover animate-slideUp stagger-${index + 3}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-bold text-gray-900">{teeTime.course_name}</p>
          <p className="text-xs text-gray-500 mt-0.5">{formatDate(teeTime.tee_datetime)}</p>
        </div>
        <span className="text-xs font-semibold text-green-900">{formatJPY(teeTime.price_per_player)}</span>
      </div>
      <div className={`inline-flex mt-3 items-center gap-1.5 rounded-full border px-2.5 py-1 ${weatherTone}`}>
        <WeatherIcon size={11} />
        <span className="text-[10px] font-bold uppercase tracking-wide">{weatherAssessment || 'Weather'}</span>
      </div>
      <p className="mt-3 text-xs text-gray-600 leading-relaxed">{recommendation.recommendation_reason}</p>
      {recommendation.weather_message && (
        <p className="mt-2 text-xs text-gray-400 leading-relaxed">{recommendation.weather_message}</p>
      )}
    </div>
  )
}

function CourseCard({
  course,
  image,
  onSelect,
  formatDate,
  weather,
  index,
}: {
  course: CourseData
  image: string
  onSelect: (c: CourseData) => void
  formatDate: (s: string | null) => string
  weather?: WeatherSummary | null
  index: number
}) {
  const WeatherIcon =
    weather?.assessment === 'good'
      ? SunMedium
      : weather?.assessment === 'bad'
        ? CloudRain
        : CloudSun

  const weatherTone =
    weather?.assessment === 'good'
      ? 'bg-emerald-50/90 text-emerald-700 border-emerald-200'
      : weather?.assessment === 'bad'
        ? 'bg-rose-50/90 text-rose-700 border-rose-200'
        : 'bg-amber-50/90 text-amber-700 border-amber-200'

  const weatherLabel =
    weather?.assessment === 'good'
      ? 'Good Weather'
      : weather?.assessment === 'bad'
        ? 'Tough Weather'
        : 'Mixed Weather'

  return (
    <div className={`bg-white rounded-2xl overflow-hidden shadow-soft card-hover animate-slideUp stagger-${(index % 6) + 1}`}>
      <div className="relative h-40 overflow-hidden">
        <img src={image} alt={course.name} className="w-full h-full object-cover img-zoom" />
        {course.rating && (
          <div className="absolute top-2.5 right-2.5 glass rounded-full px-2.5 py-1 flex items-center gap-1">
            <Star size={10} fill="#c8922a" color="#c8922a" />
            <span className="text-xs font-bold text-gray-800">{course.rating}</span>
          </div>
        )}
        {course.amenities.includes('caddie_service') && (
          <div className="absolute top-2.5 left-2.5 bg-gold-500/90 backdrop-blur-sm text-white text-[10px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full flex items-center gap-1">
            <Lock size={8} />
            Member Exclusive
          </div>
        )}
        {weather?.assessment && (
          <div className={`absolute bottom-2.5 left-2.5 backdrop-blur-sm border rounded-full px-2.5 py-1 flex items-center gap-1.5 ${weatherTone}`}>
            <WeatherIcon size={11} />
            <span className="text-[10px] font-bold uppercase tracking-wide">{weatherLabel}</span>
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
              from {formatJPY(course.min_price)}
            </span>
          )}
        </div>
        <div className="mt-3 flex items-end justify-between">
          <div>
            <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide">Next Available</p>
            <p className="text-sm font-bold text-gray-900">{formatDate(course.next_available)}</p>
            {weather?.message && (
              <p className="text-xs text-gray-500 mt-1 max-w-[15rem] line-clamp-2">{weather.message}</p>
            )}
          </div>
          <button
            onClick={() => onSelect(course)}
            className="bg-gradient-to-r from-green-900 to-green-800 text-white text-xs font-semibold px-4 py-2 rounded-xl hover:shadow-glow transition-all duration-200 hover:scale-[1.02] active:scale-[.98]"
          >
            Select
          </button>
        </div>
      </div>
    </div>
  )
}
