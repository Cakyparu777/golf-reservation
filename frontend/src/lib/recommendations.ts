export interface RecommendedTeeTime {
  tee_time: {
    id: number
    course_id: number
    tee_datetime: string
    available_slots: number
    price_per_player: number
    course_name?: string
    course_location?: string
  }
  weather_assessment?: 'good' | 'mixed' | 'bad'
  weather_message?: string
  recommendation_reason: string
  score: number
}

export interface RecommendationResponse {
  recommended_tee_times: RecommendedTeeTime[]
  message: string
}

export async function fetchRecommendations(params: {
  date: string
  numPlayers?: number
  preferredTime?: 'morning' | 'afternoon' | 'evening'
  userArea?: string
  travelMode?: 'train' | 'car' | 'either'
  maxTravelMinutes?: number
  maxResults?: number
}): Promise<RecommendationResponse> {
  const search = new URLSearchParams({
    date: params.date,
    num_players: String(params.numPlayers ?? 1),
    max_results: String(params.maxResults ?? 3),
  })

  if (params.preferredTime) {
    search.set('preferred_time', params.preferredTime)
  }
  if (params.userArea) {
    search.set('user_area', params.userArea)
  }
  if (params.travelMode) {
    search.set('travel_mode', params.travelMode)
  }
  if (params.maxTravelMinutes) {
    search.set('max_travel_minutes', String(params.maxTravelMinutes))
  }

  const response = await fetch(`/api/recommendations?${search.toString()}`)
  if (!response.ok) {
    throw new Error('Recommendation lookup failed.')
  }

  return response.json()
}
