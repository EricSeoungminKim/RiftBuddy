import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ChampionSlot from '../components/ChampionSlot'
import RecommendPanel from '../components/RecommendPanel'
import LaningPanel from '../components/LaningPanel'
import SynergyPanel from '../components/SynergyPanel'
import { useDraftAnalysis } from '../hooks/useDraftAnalysis'
import { useChampSelect } from '../hooks/useChampSelect'

const ROLES = ['탑', '정글', '미드', '바텀', '서폿']

type Team = [string, string, string, string, string]

const EMPTY_TEAM: Team = ['', '', '', '', '']

function toTeam(arr: string[]): Team {
  const t: Team = [...EMPTY_TEAM]
  arr.slice(0, 5).forEach((v, i) => { t[i] = v })
  return t
}

export default function DraftPage() {
  const navigate = useNavigate()
  const [ally, setAlly] = useState<Team>([...EMPTY_TEAM])
  const [enemy, setEnemy] = useState<Team>([...EMPTY_TEAM])
  const [selectedAllyIdx, setSelectedAllyIdx] = useState<number | null>(null)
  const [championInput, setChampionInput] = useState('')
  const [myRole, setMyRole] = useState('미드')
  const prevAllyRef = useRef<string>('')
  const prevEnemyRef = useRef<string>('')

  const { analysis, matchup, teamStrategy, loading, error, fetchAnalysis, fetchMatchup, fetchTeamStrategy } = useDraftAnalysis()
  const champSelect = useChampSelect(true)

  // Sync LCU picks into slots (only update changed slots)
  useEffect(() => {
    if (!champSelect.inProgress) return
    const allyKey = champSelect.ally.join(',')
    const enemyKey = champSelect.enemy.join(',')
    if (allyKey !== prevAllyRef.current) {
      prevAllyRef.current = allyKey
      setAlly(toTeam(champSelect.ally))
    }
    if (enemyKey !== prevEnemyRef.current) {
      prevEnemyRef.current = enemyKey
      setEnemy(toTeam(champSelect.enemy))
    }
  }, [champSelect])

  useEffect(() => {
    const allFilled = ally.every(Boolean) && enemy.every(Boolean)
    if (allFilled) navigate('/post-lock-in')
  }, [ally, enemy, navigate])

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
      fetchAnalysis(name, ROLES[selectedAllyIdx])
    }
  }

  const handleAssignEnemy = (idx: number) => {
    const name = prompt(`적군 ${ROLES[idx]} 챔피언 이름:`)
    if (!name) return
    const next: Team = [...enemy] as Team
    next[idx] = name
    setEnemy(next)
    // fetch matchup if we have corresponding ally
    if (ally[idx]) fetchMatchup(ally[idx], name, ROLES[idx])
  }

  const handleFetchStrategy = () => {
    const allyList = ally.filter(Boolean)
    const enemyList = enemy.filter(Boolean)
    if (allyList.length < 2) return
    const myChampion = ally[ROLES.indexOf(myRole)] || ally.find(Boolean) || ''
    fetchTeamStrategy(allyList, enemyList, myChampion, myRole)
  }

  const pageStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#0d0e1a',
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
        <h2 style={{ margin: 0, fontSize: 16, color: '#f0c040' }}>RiftBuddy — 챔피언 선택</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#888' }}>내 역할:</span>
          <select
            value={myRole}
            onChange={e => setMyRole(e.target.value)}
            style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #2a2d4a', borderRadius: 4, padding: '2px 6px', fontSize: 12 }}
          >
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
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
                role={ROLES[i]}
                isAlly={true}
                size={56}
                selected={selectedAllyIdx === i}
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
                role={ROLES[i]}
                isAlly={false}
                size={56}
                onClick={() => handleAssignEnemy(i)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Champion input for ally */}
      {selectedAllyIdx !== null && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#888' }}>{ROLES[selectedAllyIdx]} 챔피언:</span>
          <input
            autoFocus
            value={championInput}
            onChange={e => setChampionInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAssignChampion()}
            placeholder="e.g. Ahri"
            style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #3a8fd1', borderRadius: 4, padding: '4px 8px', fontSize: 13, width: 140 }}
          />
          <button
            onClick={handleAssignChampion}
            style={{ background: '#3a8fd1', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 13 }}
          >
            확인
          </button>
        </div>
      )}

      {/* Analysis Panels */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <RecommendPanel analysis={analysis} loading={loading} error={error} />
        <LaningPanel matchup={matchup} loading={loading} error={error} />
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
