import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ChampionSlot from '../components/ChampionSlot'
import DraftRecommendPanel from '../components/DraftRecommendPanel'
import TeamCompPanel from '../components/TeamCompPanel'
import OpponentMatchupPanel from '../components/OpponentMatchupPanel'
import { useDraftAnalysis } from '../hooks/useDraftAnalysis'
import { ChampSelectSlot, useChampSelect } from '../hooks/useChampSelect'

const ROLES = ['탑', '정글', '미드', '바텀', '서폿']
const ROLE_BY_LCU: Record<string, string> = {
  top: '탑', jungle: '정글', middle: '미드', bottom: '바텀', utility: '서폿',
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
  const [myRole, setMyRole] = useState('바텀')
  const prevAllyRef = useRef('')
  const prevEnemyRef = useRef('')
  const prevRoleRef = useRef('')
  const prevRecommendKeyRef = useRef('')
  const prevStrategyKeyRef = useRef('')
  const prevMatchupKeyRef = useRef('')

  const {
    matchups, teamStrategy, recommendForRole,
    loadingRecommend, loadingMatchups, loadingStrategy,
    fetchRecommendForRole, fetchMatchup, fetchTeamStrategy, reset,
  } = useDraftAnalysis()

  const champSelect = useChampSelect(true)
  const roleLabels = ROLES.map((role, i) => roleLabel(champSelect.allySlots[i], role))
  const mySlotIndex = Math.max(0, champSelect.allySlots.findIndex(slot => slot.cellId === champSelect.myCell))

  // Sync LCU picks
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

  // Auto-detect my role from LCU
  useEffect(() => {
    if (!champSelect.inProgress || mySlotIndex < 0) return
    const detectedRole = roleLabels[mySlotIndex]
    if (detectedRole && detectedRole !== prevRoleRef.current) {
      prevRoleRef.current = detectedRole
      setMyRole(detectedRole)
    }
  }, [champSelect.inProgress, mySlotIndex, roleLabels.join('|')])

  // Auto-fetch recommend when ally/enemy/role changes
  useEffect(() => {
    const allyList = ally.filter(Boolean)
    const key = `${allyList.join(',')}|${enemy.filter(Boolean).join(',')}|${myRole}`
    if (key === prevRecommendKeyRef.current) return
    prevRecommendKeyRef.current = key
    fetchRecommendForRole(allyList, enemy.filter(Boolean), myRole)
  }, [ally, enemy, myRole, fetchRecommendForRole])

  // Auto-fetch team strategy when 2+ ally picks
  useEffect(() => {
    const allyList = ally.filter(Boolean)
    const enemyList = enemy.filter(Boolean)
    if (allyList.length < 2) return
    const key = `${allyList.join(',')}|${enemyList.join(',')}|${myRole}`
    if (key === prevStrategyKeyRef.current) return
    prevStrategyKeyRef.current = key
    const myChampion = ally[mySlotIndex] || allyList[0] || ''
    fetchTeamStrategy(allyList, enemyList, myChampion, myRole)
  }, [ally, enemy, myRole, mySlotIndex, fetchTeamStrategy])

  // Auto-fetch opponent matchup winrates vs recommended pick
  useEffect(() => {
    const recommendedChamp = recommendForRole?.recommendations?.[0]?.champion
    if (!recommendedChamp) return
    const enemyList = enemy.filter(Boolean)
    if (!enemyList.length) return
    const key = `${recommendedChamp}|${enemyList.join(',')}|${myRole}`
    if (key === prevMatchupKeyRef.current) return
    prevMatchupKeyRef.current = key
    enemyList.forEach((enemyChamp, i) => {
      fetchMatchup(recommendedChamp, enemyChamp, myRole, i)
    })
  }, [recommendForRole, enemy, myRole, fetchMatchup])

  // Reset on champ select end
  useEffect(() => {
    if (!champSelect.inProgress) {
      reset()
      prevRecommendKeyRef.current = ''
      prevStrategyKeyRef.current = ''
      prevMatchupKeyRef.current = ''
    }
  }, [champSelect.inProgress, reset])

  const recommendedChamp = recommendForRole?.recommendations?.[0]?.champion ?? ''

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

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, color: '#f0c040' }}>RiftBuddy — 챔피언 선택</h2>
          <div style={{ fontSize: 11, color: champSelect.inProgress ? '#56f39a' : '#777', marginTop: 3 }}>
            {champSelect.inProgress
              ? `LCU 연결됨 · 내 역할: ${myRole}`
              : champSelect.available ? 'League 클라이언트 연결됨 · 챔피언 선택 대기 중'
              : 'League 클라이언트 실행 대기 중'}
          </div>
        </div>
      </div>

      {/* Pick Grid */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>아군</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {ally.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={roleLabels[i]}
                isAlly={true}
                size={56}
                selected={mySlotIndex === i}
                completed={champSelect.allySlots[i]?.completed ?? true}
                cellId={champSelect.allySlots[i]?.cellId}
                onClick={() => {}}
              />
            ))}
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <div>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>적군</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {enemy.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={roleLabels[i]}
                isAlly={false}
                size={56}
                selected={false}
                completed={champSelect.enemySlots[i]?.completed ?? true}
                cellId={champSelect.enemySlots[i]?.cellId}
                onClick={() => {}}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Analysis Panels */}
      <div style={{ display: 'flex', gap: 12, flex: 1, minHeight: 0 }}>
        <DraftRecommendPanel
          recommendations={recommendForRole?.recommendations ?? []}
          meta={recommendForRole?.meta ?? []}
          myRole={myRole}
          loading={loadingRecommend}
        />
        <OpponentMatchupPanel
          recommendedChampion={recommendedChamp}
          enemyChampions={enemy}
          matchups={matchups}
          loading={loadingMatchups}
          myRole={myRole}
        />
        <TeamCompPanel
          strategy={teamStrategy}
          loading={loadingStrategy}
        />
      </div>
    </div>
  )
}
