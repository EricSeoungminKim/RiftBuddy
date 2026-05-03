import { useEffect, useRef, useState } from 'react'

const BASE = import.meta.env.VITE_RIFTBUDDY_API_URL ?? 'http://localhost:8001'
const POLL_MS = 3000

export interface ChampSelectState {
  ally: string[]   // English champion IDs, up to 5
  enemy: string[]  // English champion IDs, up to 5
  allySlots: ChampSelectSlot[]
  enemySlots: ChampSelectSlot[]
  myCell: number
  inProgress: boolean
  available: boolean
  reason?: string
}

export interface ChampSelectSlot {
  cellId: number
  slot: number
  champion: string
  championId: number
  completed: boolean
  assignedPosition: string
  summonerId?: number
}

export function useChampSelect(enabled: boolean) {
  const [state, setState] = useState<ChampSelectState>({
    ally: [],
    enemy: [],
    allySlots: [],
    enemySlots: [],
    myCell: -1,
    inProgress: false,
    available: false,
  })
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!enabled) return

    async function poll() {
      try {
        const res = await fetch(`${BASE}/lcu/champ-select/status`)
        if (!res.ok) return
        const data = await res.json()
        if (!data.inProgress) {
          setState({
            ally: [],
            enemy: [],
            allySlots: [],
            enemySlots: [],
            myCell: -1,
            inProgress: false,
            available: data.available ?? false,
            reason: data.reason,
          })
          return
        }
        setState({
          ally: data.ally ?? [],
          enemy: data.enemy ?? [],
          allySlots: data.allySlots ?? [],
          enemySlots: data.enemySlots ?? [],
          myCell: data.myCell ?? -1,
          inProgress: true,
          available: data.available ?? true,
          reason: undefined,
        })
      } catch {
        // League client not running — silent
      }
    }

    poll()
    intervalRef.current = setInterval(poll, POLL_MS)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [enabled])

  return state
}
