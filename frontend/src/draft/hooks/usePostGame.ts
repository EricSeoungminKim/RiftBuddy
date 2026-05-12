import { useState, useCallback } from 'react'

const BASE = import.meta.env.VITE_RIFTBUDDY_API_URL ?? 'http://localhost:8001'

export interface CoachReport {
  strengths: string
  improvements: string
  moments: string
  goals: string
  metrics: PostGameMetrics
  timeline: TimelinePoint[]
  keyMoments: string[]
}

export interface PostGameMetrics {
  champion: string
  position: string
  durationMinutes: number
  kills: number
  deaths: number
  assists: number
  finalCs: number
  csPerMinute: number
  csVsAvgPct: number | null
  avgGoldDiff: number
  score: number
  seedSaved: boolean
  seedDocId: string | null
  benchmarkSource: string
}

export interface TimelinePoint {
  minute: number
  cs: number
  goldDiff: number
  healthPercent: number
  kills: number
  deaths: number
  assists: number
}

export interface PostGameState {
  report: CoachReport | null
  loading: boolean
  error: string | null
}

export function usePostGame() {
  const [state, setState] = useState<PostGameState>({
    report: null,
    loading: false,
    error: null,
  })

  const fetchReport = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      const res = await fetch(`${BASE}/postgame/coach`, { method: 'POST' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `HTTP ${res.status}`)
      }
      const data: CoachReport = await res.json()
      setState({ report: data, loading: false, error: null })
    } catch (e) {
      setState(prev => ({ ...prev, loading: false, error: String(e) }))
    }
  }, [])

  const clearSnapshots = useCallback(async () => {
    await fetch(`${BASE}/game/snapshots`, { method: 'DELETE' }).catch(() => null)
    setState({ report: null, loading: false, error: null })
  }, [])

  return { ...state, fetchReport, clearSnapshots }
}
