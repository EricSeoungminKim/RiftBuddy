import React, { useEffect, useRef, useState } from 'react'
import ChampionSlot from '../components/ChampionSlot'
import DraftRecommendPanel from '../components/DraftRecommendPanel'
import TeamCompPanel from '../components/TeamCompPanel'
import OpponentMatchupPanel from '../components/OpponentMatchupPanel'
import { useDraftAnalysis } from '../hooks/useDraftAnalysis'
import { ChampSelectSlot, useChampSelect } from '../hooks/useChampSelect'
import {
  championForMatchups,
  shouldFetchRoleRecommendations,
  shouldFetchTeamStrategy,
} from '../automation'
import { ROLES, Role, findLocalPlayerSlotIndex, resolveSelectedRole, roleLabel } from '../role'

type Team = [string, string, string, string, string]
const EMPTY_TEAM: Team = ['', '', '', '', '']

function toTeam(arr: string[]): Team {
  const t: Team = [...EMPTY_TEAM]
  arr.slice(0, 5).forEach((v, i) => { t[i] = v })
  return t
}

function slotsToTeam(slots: ChampSelectSlot[]): Team {
  const t = [...EMPTY_TEAM] as Team
  slots.slice(0, 5).forEach((slot, i) => { t[i] = slot.champion || t[i] || '' })
  return t
}

export default function DraftPage() {
  const [ally, setAlly] = useState<Team>([...EMPTY_TEAM])
  const [enemy, setEnemy] = useState<Team>([...EMPTY_TEAM])
  const [myRole, setMyRole] = useState<Role>('탑')
  const [selectedRoleIndex, setSelectedRoleIndex] = useState(0)
  const prevAllyRef = useRef('')
  const prevEnemyRef = useRef('')
  const prevLocalSlotRef = useRef(-1)
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
  const lcuSlotIndex = findLocalPlayerSlotIndex(champSelect.allySlots, champSelect.myCell)
  const mySlotIndex = lcuSlotIndex >= 0 ? lcuSlotIndex : selectedRoleIndex

  // Sync LCU picks
  useEffect(() => {
    if (!champSelect.inProgress) return
    const allyKey = JSON.stringify(champSelect.allySlots)
    const enemyKey = JSON.stringify(champSelect.enemySlots)
    if (allyKey !== prevAllyRef.current) {
      prevAllyRef.current = allyKey
      setAlly(slotsToTeam(champSelect.allySlots))
    }
    if (enemyKey !== prevEnemyRef.current) {
      prevEnemyRef.current = enemyKey
      setEnemy(slotsToTeam(champSelect.enemySlots))
    }
  }, [champSelect])

  // Auto-detect my role from LCU
  useEffect(() => {
    if (!champSelect.inProgress || lcuSlotIndex < 0) return
    const detectedRole = resolveSelectedRole(roleLabels, lcuSlotIndex, myRole)
    if (detectedRole !== myRole || lcuSlotIndex !== prevLocalSlotRef.current) {
      prevLocalSlotRef.current = lcuSlotIndex
      setSelectedRoleIndex(lcuSlotIndex)
      setMyRole(detectedRole)
    }
  }, [champSelect.inProgress, lcuSlotIndex, myRole, roleLabels.join('|')])

  // Auto-fetch recommend when ally/enemy/role changes
  useEffect(() => {
    if (!shouldFetchRoleRecommendations(champSelect.inProgress)) return
    const allyList = ally.filter(Boolean)
    const key = `${allyList.join(',')}|${enemy.filter(Boolean).join(',')}|${myRole}`
    if (key === prevRecommendKeyRef.current) return
    prevRecommendKeyRef.current = key
    fetchRecommendForRole(allyList, enemy.filter(Boolean), myRole)
  }, [ally, enemy, myRole, champSelect.inProgress, fetchRecommendForRole])

  // Auto-fetch team strategy after both teams finish all five picks.
  useEffect(() => {
    const allyList = ally.filter(Boolean)
    const enemyList = enemy.filter(Boolean)
    const allyCompleted = champSelect.allySlots.slice(0, 5).map(slot => slot.completed)
    const enemyCompleted = champSelect.enemySlots.slice(0, 5).map(slot => slot.completed)
    if (!shouldFetchTeamStrategy(ally, enemy, allyCompleted, enemyCompleted)) return
    const matchupList = Object.values(matchups)
    const matchupKey = matchupList.map(item => `${item.enemyChampion}:${item.winRate ?? ''}`).join(',')
    const key = `${allyList.join(',')}|${enemyList.join(',')}|${myRole}|${matchupKey}`
    if (key === prevStrategyKeyRef.current) return
    prevStrategyKeyRef.current = key
    const myChampion = ally[mySlotIndex] || allyList[0] || ''
    fetchTeamStrategy(allyList, enemyList, myChampion, myRole, matchupList)
  }, [ally, enemy, myRole, mySlotIndex, matchups, champSelect.allySlots, champSelect.enemySlots, fetchTeamStrategy])

  // Auto-fetch opponent matchup winrates vs recommended pick
  useEffect(() => {
    const recommendedChamp = recommendForRole?.recommendations?.[0]?.champion
    const matchupChampion = championForMatchups(ally, mySlotIndex, recommendedChamp ?? '')
    if (!matchupChampion) return
    const enemyList = enemy.filter(Boolean)
    if (!enemyList.length) return
    const key = `${matchupChampion}|${enemyList.join(',')}|${myRole}`
    if (key === prevMatchupKeyRef.current) return
    prevMatchupKeyRef.current = key
    enemyList.forEach((enemyChamp, i) => {
      fetchMatchup(matchupChampion, enemyChamp, myRole, i)
    })
  }, [recommendForRole, ally, enemy, myRole, mySlotIndex, fetchMatchup])

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
  const matchupChampion = championForMatchups(ally, mySlotIndex, recommendedChamp)

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
          <h2 style={{ margin: 0, fontSize: 18, color: '#f0c040' }}>RiftBuddy Draft</h2>
          <div style={{ fontSize: 11, color: champSelect.inProgress ? '#56f39a' : '#777', marginTop: 3 }}>
            {champSelect.inProgress
              ? `LCU connected · role: ${myRole}`
              : champSelect.available ? 'League client connected · waiting for champion select'
              : champSelect.reason === 'backend_unreachable'
                ? `RiftBuddy backend unavailable · ${champSelect.message ?? 'status unknown'}`
                : 'Waiting for League client'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {ROLES.map((role, index) => (
            <button
              key={role}
              type="button"
              onClick={() => {
                setSelectedRoleIndex(index)
                setMyRole(role)
              }}
              style={{
                border: `1px solid ${myRole === role ? '#f0c040' : '#2a2d4a'}`,
                background: myRole === role ? '#f0c040' : '#12131f',
                color: myRole === role ? '#080a12' : '#aaa',
                borderRadius: 6,
                padding: '5px 9px',
                fontSize: 12,
                fontWeight: myRole === role ? 700 : 500,
                cursor: 'pointer',
              }}
            >
              {role}
            </button>
          ))}
        </div>
      </div>

      {/* Pick Grid */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Ally</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {ally.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={`Slot ${i + 1} · ${roleLabels[i]}`}
                isAlly={true}
                size={56}
                selected={mySlotIndex === i}
                completed={champSelect.allySlots[i]?.completed ?? true}
                onClick={() => {
                  setSelectedRoleIndex(i)
                  setMyRole(roleLabels[i])
                }}
              />
            ))}
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <div>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>Enemy</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {enemy.map((id, i) => (
              <ChampionSlot
                key={i}
                championId={id || undefined}
                role={`Slot ${i + 1}`}
                isAlly={false}
                size={56}
                selected={false}
                completed={champSelect.enemySlots[i]?.completed ?? true}
                onClick={() => {}}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Analysis Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, flex: 1, minHeight: 0 }}>
        <DraftRecommendPanel
          recommendations={recommendForRole?.recommendations ?? []}
          meta={recommendForRole?.meta ?? []}
          myRole={myRole}
          loading={loadingRecommend}
        />
        <OpponentMatchupPanel
          recommendedChampion={matchupChampion}
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
