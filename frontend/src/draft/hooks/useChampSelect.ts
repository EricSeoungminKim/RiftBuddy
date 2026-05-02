import { useEffect, useRef, useState } from 'react'

const BASE = import.meta.env.VITE_RIFTBUDDY_API_URL ?? 'http://localhost:8001'
const POLL_MS = 3000

export interface ChampSelectState {
  ally: string[]   // English champion IDs, up to 5
  enemy: string[]  // English champion IDs, up to 5
  inProgress: boolean
}

export function useChampSelect(enabled: boolean) {
  const [state, setState] = useState<ChampSelectState>({ ally: [], enemy: [], inProgress: false })
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!enabled) return

    async function poll() {
      try {
        const res = await fetch(`${BASE}/lcu/champ-select`)
        if (res.status === 404) {
          setState({ ally: [], enemy: [], inProgress: false })
          return
        }
        if (!res.ok) return
        const data = await res.json()
        setState({ ally: data.ally ?? [], enemy: data.enemy ?? [], inProgress: true })
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
