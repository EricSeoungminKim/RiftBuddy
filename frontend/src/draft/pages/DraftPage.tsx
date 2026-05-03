import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ChampionSlot from '../components/ChampionSlot'
import RecommendPanel from '../components/RecommendPanel'
import LaningPanel from '../components/LaningPanel'
import SynergyPanel from '../components/SynergyPanel'
import { useDraftAnalysis } from '../hooks/useDraftAnalysis'
import { ChampSelectSlot, useChampSelect } from '../hooks/useChampSelect'

const ROLES = ['탑', '정글', '미드', '바텀', '서폿']
const ROLE_BY_LCU: Record<string, string> = {
  top: '탑',
  jungle: '정글',
  middle: '미드',
  bottom: '바텀',
  utility: '서폿',
}

type Team = [string, string, string, string, string]

const EMPTY_TEAM: Team = ['', '', '', '', '']

function toTeam(arr: string[]): Team {
  const t: Team = [...EMPTY_TEAM]
  arr.slice(0, 5).forEach((v, i) => { t[i] = v })
  return t
}

function slotsToTeam(slots: ChampSelectSlot[], fallback: string[]): Team {
  const t = toTeam(fallback)
  slots.slice(0, 5).forEach((slot, i) => { t[i] = slot.champion || t[i] || '' })
  return t
}

function roleLabel(slot: ChampSelectSlot | undefined, fallback: string): string {
  const raw = slot?.assignedPosition?.toLowerCase()
  return raw ? ROLE_BY_LCU[raw] ?? fallback : fallback
}

export default function DraftPage() {
  const navigate = useNavigate()
  const [ally, setAlly] = useState<Team>([...EMPTY_TEAM])
  const [enemy, setEnemy] = useState<Team>([...EMPTY_TEAM])
  const [selectedAllyIdx, setSelectedAllyIdx] = useState<number | null>(null)
  const [selectedEnemyIdx, setSelectedEnemyIdx] = useState<number | null>(null)
  const [championInput, setChampionInput] = useState('')
  const [enemyInput, setEnemyInput] = useState('')
  const [myRole, setMyRole] = useState('미드')
  const prevAllyRef = useRef<string>('')
  const prevEnemyRef = useRef<string>('')
  const prevMatchupKeyRef = useRef<string>('')

  const {
    analysis,
    matchup,
    matchups,
    teamStrategy,
    loading,
    error,
    fetchAnalysis,
    fetchMatchup,
    fetchTeamStrategy,
  } = useDraftAnalysis()
  const champSelect = useChampSelect(true)
  const roleLabels = ROLES.map((role, i) => roleLabel(champSelect.allySlots[i], role))
  const mySlotIndex = Math.max(0, champSelect.allySlots.findIndex(slot => slot.cellId === champSelect.myCell))

  // Sync LCU picks into stable slots. The backend returns cellId-aware slots so
  // we no longer guess based on the order of completed picks.
  useEffect(() => {
    if (!champSelect.inProgress) return
    const allyKey = JSON.stringify(champSelect.allySlots)
    const enemyKey = JSON.stringify(champSelect.enemySlots)
    if (allyKey !== prevAllyRef.current) {
      prevAllyRef.current = allyKey
      setAlly(prev => slotsToTeam(champSelect.allySlots, prev))
    }
    if (enemyKey !== prevEnemyRef.current) {
      prevEnemyRef.current = enemyKey
      setEnemy(prev => slotsToTeam(champSelect.enemySlots, prev))
    }
  }, [champSelect])

  useEffect(() => {
    if (!champSelect.inProgress) return
    if (mySlotIndex >= 0 && roleLabels[mySlotIndex]) {
      setMyRole(roleLabels[mySlotIndex])
      setSelectedAllyIdx(mySlotIndex)
    }
  }, [champSelect.inProgress, mySlotIndex, roleLabels.join('|')])

  useEffect(() => {
    const pairs = ally
      .map((champion, i) => ({ champion, enemy: enemy[i], role: roleLabels[i], slot: i }))
      .filter(pair => pair.champion && pair.enemy)
    const key = pairs.map(pair => `${pair.slot}:${pair.champion}:${pair.enemy}:${pair.role}`).join('|')
    if (!key || key === prevMatchupKeyRef.current) return
    prevMatchupKeyRef.current = key
    pairs.forEach(pair => fetchMatchup(pair.champion, pair.enemy, pair.role, pair.slot))
  }, [ally, enemy, fetchMatchup, roleLabels.join('|')])

  useEffect(() => {
    const allFilled = ally.every(Boolean) && enemy.every(Boolean)
    const allCompleted = [...champSelect.allySlots, ...champSelect.enemySlots].filter(Boolean).length >= 10
      && [...champSelect.allySlots, ...champSelect.enemySlots].every(slot => slot.completed)
    // Only auto-navigate when LCU is driving picks (not manual input)
    if (allFilled && allCompleted && champSelect.inProgress) navigate('/post-lock-in')
  }, [ally, enemy, navigate, champSelect.inProgress, champSelect.allySlots, champSelect.enemySlots])

  const handleAllySlotClick = (idx: number) => {
    setSelectedAllyIdx(idx === selectedAllyIdx ? null : idx)
  }

  const handleAssignChampion = () => {
    if (!championInput.trim()) return
    const name = championInput.trim()
    if (selectedAllyIdx !== null) {
      const next: Team = [...ally] as Team
      next[selectedAllyIdx] = name
      setAlly(next)
      setSelectedAllyIdx(null)
      setChampionInput('')
      fetchAnalysis(name, roleLabels[selectedAllyIdx])
    }
  }

  const handleEnemySlotClick = (idx: number) => {
    setSelectedEnemyIdx(idx === selectedEnemyIdx ? null : idx)
  }

  const handleAssignEnemy = () => {
    if (!enemyInput.trim() || selectedEnemyIdx === null) return
    const name = enemyInput.trim()
    const next: Team = [...enemy] as Team
    next[selectedEnemyIdx] = name
    setEnemy(next)
    if (ally[selectedEnemyIdx]) fetchMatchup(ally[selectedEnemyIdx], name, roleLabels[selectedEnemyIdx], selectedEnemyIdx)
    setSelectedEnemyIdx(null)
    setEnemyInput('')
  }

  const handleFetchStrategy = () => {
    const allyList = ally.filter(Boolean)
    const enemyList = enemy.filter(Boolean)
    if (allyList.length < 2) return
    const myChampion = ally[roleLabels.indexOf(myRole)] || ally[mySlotIndex] || ally.find(Boolean) || ''
    fetchTeamStrategy(allyList, enemyList, myChampion, myRole)
  }

  const pageStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: 'radial-gradient(circle at 20% -10%, rgba(49,83,122,0.24), transparent 34%), #080a12',
    color: '#e0e0e0',
    fontFamily: 'sans-serif',
    padding: 16,
    boxSizing: 'border-box',
    gap: 12,
  }

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    gap: 8,
    alignItems: 'flex-start',
  }

  const sectionLabel: React.CSSProperties = {
    fontSize: 11,
    color: '#888',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 1,
  }

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: '#f0c040' }}>RiftBuddy — 챔피언 선택</h2>
          <div style={{ fontSize: 11, color: champSelect.inProgress ? '#56f39a' : '#777', marginTop: 3 }}>
            {champSelect.inProgress
              ? `LCU 연결됨 · 내 cell ${champSelect.myCell}`
              : champSelect.available
              ? 'League 클라이언트 연결됨 · 챔피언 선택 대기 중'
              : 'League 클라이언트 실행 대기 중'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#888' }}>내 역할:</span>
          <select
            value={myRole}
            onChange={e => setMyRole(e.target.value)}
            style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #2a2d4a', borderRadius: 4, padding: '2px 6px', fontSize: 12 }}
          >
            {roleLabels.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {/* Pick Grid */}
      <div style={rowStyle}>
        {/* Ally */}
        <div>
          <div style={sectionLabel}>아군</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {ally.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={roleLabels[i]}
                isAlly={true}
                size={56}
                selected={selectedAllyIdx === i}
                completed={champSelect.allySlots[i]?.completed ?? true}
                cellId={champSelect.allySlots[i]?.cellId}
                onClick={() => handleAllySlotClick(i)}
              />
            ))}
          </div>
        </div>
        {/* Spacer */}
        <div style={{ flex: 1 }} />
        {/* Enemy */}
        <div>
          <div style={sectionLabel}>적군</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {enemy.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={roleLabels[i]}
                isAlly={false}
                size={56}
                selected={selectedEnemyIdx === i}
                completed={champSelect.enemySlots[i]?.completed ?? true}
                cellId={champSelect.enemySlots[i]?.cellId}
                onClick={() => handleEnemySlotClick(i)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Champion input for ally */}
      {selectedAllyIdx !== null && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#888' }}>아군 {roleLabels[selectedAllyIdx]}:</span>
          <input
            autoFocus
            value={championInput}
            onChange={e => setChampionInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAssignChampion()}
            placeholder="e.g. Ahri"
            style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #3a8fd1', borderRadius: 4, padding: '4px 8px', fontSize: 13, width: 140 }}
          />
          <button onClick={handleAssignChampion} style={{ background: '#3a8fd1', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 13 }}>확인</button>
        </div>
      )}
      {/* Champion input for enemy */}
      {selectedEnemyIdx !== null && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#e05050' }}>적군 {roleLabels[selectedEnemyIdx]}:</span>
          <input
            autoFocus
            value={enemyInput}
            onChange={e => setEnemyInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAssignEnemy()}
            placeholder="e.g. Zed"
            style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #e05050', borderRadius: 4, padding: '4px 8px', fontSize: 13, width: 140 }}
          />
          <button onClick={handleAssignEnemy} style={{ background: '#e05050', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 13 }}>확인</button>
        </div>
      )}

      {/* Analysis Panels */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <RecommendPanel analysis={analysis} loading={loading} error={error} />
        <LaningPanel matchup={matchup} matchups={matchups} roles={roleLabels} activeSlot={selectedAllyIdx ?? mySlotIndex} loading={loading} error={error} />
        <SynergyPanel strategy={teamStrategy} loading={loading} error={error} />
      </div>

      {/* Strategy button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleFetchStrategy}
          disabled={ally.filter(Boolean).length < 2}
          style={{
            background: ally.filter(Boolean).length < 2 ? '#2a2d4a' : '#f0c040',
            color: ally.filter(Boolean).length < 2 ? '#555' : '#0d0e1a',
            border: 'none',
            borderRadius: 4,
            padding: '8px 20px',
            cursor: ally.filter(Boolean).length < 2 ? 'not-allowed' : 'pointer',
            fontWeight: 'bold',
            fontSize: 13,
          }}
        >
          팀 시너지 분석
        </button>
      </div>
    </div>
  )
}
