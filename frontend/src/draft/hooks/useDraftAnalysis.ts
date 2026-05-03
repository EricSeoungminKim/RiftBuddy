import { useState, useCallback } from 'react'

const BASE = import.meta.env.VITE_RIFTBUDDY_API_URL ?? 'http://localhost:8001'

export interface ChampionAnalysis {
  champion: string
  role: string
  winRate?: number
  tier?: string
  tips?: string[]
  raw: unknown
}

export interface MatchupGuide {
  myChampion: string
  enemyChampion: string
  role: string
  slot?: number
  winRate?: number
  pickRate?: number
  advantage?: string
  tips?: string[]
  raw: unknown
}

export interface RuneRecommendation {
  primaryStyleId: number
  subStyleId: number
  selectedPerkIds: number[]
  name: string
  raw: unknown
}

export interface TeamStrategy {
  strategy: string
}

export interface DraftState {
  analysis: ChampionAnalysis | null
  matchup: MatchupGuide | null
  matchups: Record<number, MatchupGuide>
  runes: RuneRecommendation | null
  teamStrategy: TeamStrategy | null
  recommendForRole: { recommendations: { champion: string; reason: string }[]; meta: string[] } | null
  loading: boolean
  loadingRecommend: boolean
  loadingMatchups: boolean
  loadingStrategy: boolean
  error: string | null
}

export function useDraftAnalysis() {
  const [state, setState] = useState<DraftState>({
    analysis: null,
    matchup: null,
    matchups: {},
    runes: null,
    teamStrategy: null,
    recommendForRole: null,
    loading: false,
    loadingRecommend: false,
    loadingMatchups: false,
    loadingStrategy: false,
    error: null,
  })

  const setLoading = (loading: boolean) =>
    setState(prev => ({ ...prev, loading, error: loading ? null : prev.error }))

  const setError = (error: string) =>
    setState(prev => ({ ...prev, error, loading: false }))

  const fetchAnalysis = useCallback(async (champion: string, role: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/draft/champion-analysis?champion=${encodeURIComponent(champion)}&role=${encodeURIComponent(role)}`)
      if (!res.ok) throw new Error(`champion-analysis ${res.status}`)
      const raw = await res.json()
      setState(prev => ({
        ...prev,
        analysis: { champion, role, raw, winRate: raw.winRate, tier: raw.tier, tips: raw.tips },
        loading: false,
        error: null,
      }))
    } catch (e) {
      setError(String(e))
    }
  }, [])

  const fetchMatchup = useCallback(async (myChampion: string, enemyChampion: string, role: string, slot?: number) => {
    setState(prev => ({ ...prev, loadingMatchups: true }))
    try {
      const res = await fetch(`${BASE}/draft/matchup?my_champion=${encodeURIComponent(myChampion)}&enemy_champion=${encodeURIComponent(enemyChampion)}&role=${encodeURIComponent(role)}`)
      if (!res.ok) throw new Error(`matchup ${res.status}`)
      const raw = await res.json()
      const matchup = {
        myChampion,
        enemyChampion,
        role,
        slot,
        raw,
        winRate: extractNumber(raw, ['win_rate', 'winRate', 'winning_rate']),
        pickRate: extractNumber(raw, ['pick_rate', 'pickRate']),
        advantage: extractString(raw, ['advantage', 'laning_advantage', 'early_advantage']),
        tips: extractStringArray(raw, ['tips', 'guide', 'summary']),
      }
      setState(prev => ({
        ...prev,
        matchup,
        matchups: slot === undefined ? prev.matchups : { ...prev.matchups, [slot]: matchup },
        loadingMatchups: false,
        error: null,
      }))
    } catch (e) {
      setState(prev => ({ ...prev, loadingMatchups: false }))
      setError(String(e))
    }
  }, [])

  const fetchRunes = useCallback(async (champion: string, role: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/draft/runes?champion=${encodeURIComponent(champion)}&role=${encodeURIComponent(role)}`)
      if (!res.ok) throw new Error(`runes ${res.status}`)
      const raw = await res.json()
      setState(prev => ({
        ...prev,
        runes: {
          raw,
          primaryStyleId: raw.primaryStyleId ?? 0,
          subStyleId: raw.subStyleId ?? 0,
          selectedPerkIds: raw.selectedPerkIds ?? [],
          name: raw.name ?? `${champion} ${role} Runes`,
        },
        loading: false,
        error: null,
      }))
    } catch (e) {
      setError(String(e))
    }
  }, [])

  const fetchTeamStrategy = useCallback(async (
    ally: string[],
    enemy: string[],
    myChampion: string,
    myRole: string,
  ) => {
    setState(prev => ({ ...prev, loadingStrategy: true }))
    try {
      const res = await fetch(`${BASE}/draft/team-strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ally, enemy, my_champion: myChampion, my_role: myRole }),
      })
      if (!res.ok) throw new Error(`team-strategy ${res.status}`)
      const data = await res.json()
      setState(prev => ({
        ...prev,
        teamStrategy: { strategy: data.strategy },
        loadingStrategy: false,
        error: null,
      }))
    } catch (e) {
      setState(prev => ({ ...prev, loadingStrategy: false }))
      setError(String(e))
    }
  }, [])

  const fetchRecommendForRole = useCallback(async (ally: string[], enemy: string[], myRole: string, language = 'ko') => {
    setState(prev => ({ ...prev, loadingRecommend: true }))
    try {
      const res = await fetch(`${BASE}/draft/recommend-for-role`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ally, enemy, my_role: myRole, language }),
      })
      if (!res.ok) throw new Error(`recommend-for-role ${res.status}`)
      const data = await res.json()
      setState(prev => ({ ...prev, recommendForRole: data, loadingRecommend: false }))
    } catch (e) {
      setState(prev => ({ ...prev, loadingRecommend: false }))
    }
  }, [])

  const applyRunes = useCallback(async (page: RuneRecommendation) => {
    try {
      const res = await fetch(`${BASE}/lcu/apply-runes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: page.name,
          primaryStyleId: page.primaryStyleId,
          subStyleId: page.subStyleId,
          selectedPerkIds: page.selectedPerkIds,
        }),
      })
      if (!res.ok) throw new Error(`apply-runes ${res.status}`)
      return await res.json()
    } catch (e) {
      setError(String(e))
      return null
    }
  }, [])

  const reset = useCallback(() => {
    setState({ analysis: null, matchup: null, matchups: {}, runes: null, teamStrategy: null, recommendForRole: null, loading: false, loadingRecommend: false, loadingMatchups: false, loadingStrategy: false, error: null })
  }, [])

  return { ...state, fetchAnalysis, fetchMatchup, fetchRunes, fetchTeamStrategy, fetchRecommendForRole, applyRunes, reset }
}

function extractNumber(raw: unknown, keys: string[]): number | undefined {
  const value = findValue(raw, keys)
  if (typeof value === 'number') return value > 1 ? value : value * 100
  if (typeof value === 'string') {
    const parsed = Number(value.replace('%', ''))
    return Number.isFinite(parsed) ? parsed : undefined
  }
  return undefined
}

function extractString(raw: unknown, keys: string[]): string | undefined {
  const value = findValue(raw, keys)
  return typeof value === 'string' ? value : undefined
}

function extractStringArray(raw: unknown, keys: string[]): string[] | undefined {
  const value = findValue(raw, keys)
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string')
  if (typeof value === 'string') return [value]
  return undefined
}

function findValue(raw: unknown, keys: string[]): unknown {
  if (!raw || typeof raw !== 'object') return undefined
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (keys.includes(key)) return value
    const nested = findValue(value, keys)
    if (nested !== undefined) return nested
  }
  return undefined
}
