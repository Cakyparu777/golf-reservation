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

export async function fetchWeatherForTeeTime(courseName: string, teeDatetime: string): Promise<WeatherSummary | null> {
  if (!courseName || !teeDatetime) return null

  const parts = formatDateParts(teeDatetime)
  const params = new URLSearchParams({
    course_name: courseName,
    date: parts.date,
    time: parts.time,
  })

  const response = await fetch(`/api/weather?${params.toString()}`)
  if (!response.ok) {
    throw new Error('Weather lookup failed.')
  }

  return response.json()
}
