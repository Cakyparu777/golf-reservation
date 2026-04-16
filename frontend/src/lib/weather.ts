export interface WeatherSummary {
  course_name?: string
  requested_datetime?: string
  forecast_datetime?: string
  weather_description?: string
  assessment?: 'good' | 'mixed' | 'bad'
  message?: string
  temperature_c?: number
  precipitation_probability?: number
  wind_speed_kmh?: number
  error?: string
}

type CachedWeatherEntry = {
  data: WeatherSummary | null
  cachedAt: number
}

const WEATHER_CACHE_TTL_MS = 5 * 60 * 1000
const weatherCache = new Map<string, CachedWeatherEntry>()
const inflightRequests = new Map<string, Promise<WeatherSummary | null>>()

function formatDateParts(iso: string) {
  const date = new Date(iso)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  return {
    date: `${year}-${month}-${day}`,
    time: `${hours}:${minutes}`,
  }
}

function weatherCacheKey(courseName: string, teeDatetime: string) {
  return `${courseName}__${teeDatetime}`
}

export async function fetchWeatherForTeeTime(courseName: string, teeDatetime: string): Promise<WeatherSummary | null> {
  if (!courseName || !teeDatetime) return null

  const cacheKey = weatherCacheKey(courseName, teeDatetime)
  const cached = weatherCache.get(cacheKey)
  if (cached && Date.now() - cached.cachedAt < WEATHER_CACHE_TTL_MS) {
    return cached.data
  }

  const inflight = inflightRequests.get(cacheKey)
  if (inflight) {
    return inflight
  }

  const parts = formatDateParts(teeDatetime)
  const params = new URLSearchParams({
    course_name: courseName,
    date: parts.date,
    time: parts.time,
  })

  const request = fetch(`/api/weather?${params.toString()}`)
    .then(async (response) => {
      if (!response.ok) {
        throw new Error('Weather lookup failed.')
      }
      const data = await response.json()
      weatherCache.set(cacheKey, { data, cachedAt: Date.now() })
      return data
    })
    .finally(() => {
      inflightRequests.delete(cacheKey)
    })

  inflightRequests.set(cacheKey, request)
  return request
}
