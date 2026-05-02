import { useState, useCallback } from 'react'

const BASE = 'http://localhost:8765'

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
  runes: RuneRecommendation | null
  teamStrategy: TeamStrategy | null
  loading: boolean
  error: string | null
}

export function useDraftAnalysis() {
  const [state, setState] = useState<DraftState>({
    analysis: null,
    matchup: null,
    runes: null,
    teamStrategy: null,
    loading: false,
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

  const fetchMatchup = useCallback(async (myChampion: string, enemyChampion: string, role: string) => {
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/draft/matchup?my_champion=${encodeURIComponent(myChampion)}&enemy_champion=${encodeURIComponent(enemyChampion)}&role=${encodeURIComponent(role)}`)
      if (!res.ok) throw new Error(`matchup ${res.status}`)
      const raw = await res.json()
      setState(prev => ({
        ...prev,
        matchup: { myChampion, enemyChampion, role, raw, advantage: raw.advantage, tips: raw.tips },
        loading: false,
        error: null,
      }))
    } catch (e) {
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
    setLoading(true)
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
        loading: false,
        error: null,
      }))
    } catch (e) {
      setError(String(e))
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
    setState({ analysis: null, matchup: null, runes: null, teamStrategy: null, loading: false, error: null })
  }, [])

  return { ...state, fetchAnalysis, fetchMatchup, fetchRunes, fetchTeamStrategy, applyRunes, reset }
}
