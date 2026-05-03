import React from 'react'
import { MatchupGuide } from '../hooks/useDraftAnalysis'

interface Props {
  matchup: MatchupGuide | null
  matchups?: Record<number, MatchupGuide>
  roles?: string[]
  activeSlot?: number | null
  loading: boolean
  error: string | null
}

export default function LaningPanel({ matchup, matchups = {}, roles = [], activeSlot, loading, error }: Props) {
  const panelStyle: React.CSSProperties = {
    background: 'linear-gradient(180deg, rgba(24,27,43,0.98), rgba(10,12,22,0.98))',
    border: '1px solid rgba(96,120,170,0.38)',
    borderRadius: 8,
    padding: 16,
    color: '#e0e0e0',
    minHeight: 200,
    flex: 1,
  }

  if (loading) return <div style={panelStyle}><span style={{ color: '#888' }}>매치업 분석 중...</span></div>
  if (error) return <div style={panelStyle}><span style={{ color: '#d13a3a' }}>{error}</span></div>
  const matchupList = Object.entries(matchups)
    .map(([slot, value]) => ({ slot: Number(slot), value }))
    .sort((a, b) => a.slot - b.slot)

  if (!matchup && matchupList.length === 0) return (
    <div style={panelStyle}>
      <span style={{ color: '#555' }}>아군과 적군 챔피언을 선택하면 라이닝 가이드가 표시됩니다</span>
    </div>
  )

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: '0 0 12px', color: '#f0c040', fontSize: 14 }}>
        실시간 매치업
      </h3>
      {(matchupList.length > 0 ? matchupList : [{ slot: activeSlot ?? 0, value: matchup as MatchupGuide }]).map(({ slot, value }) => (
        <div
          key={`${value.myChampion}-${value.enemyChampion}-${slot}`}
          style={{
            border: `1px solid ${slot === activeSlot ? 'rgba(240,192,64,0.85)' : 'rgba(255,255,255,0.08)'}`,
            background: slot === activeSlot ? 'rgba(240,192,64,0.08)' : 'rgba(255,255,255,0.035)',
            borderRadius: 6,
            padding: 10,
            marginBottom: 8,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
            <strong style={{ fontSize: 13 }}>{value.myChampion} vs {value.enemyChampion}</strong>
            <span style={{ fontSize: 11, color: '#9fb2d8' }}>{roles[slot] ?? value.role}</span>
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: 12 }}>
            {value.winRate !== undefined && (
              <span><span style={{ color: '#888' }}>승률 </span><b>{value.winRate.toFixed(1)}%</b></span>
            )}
            {value.pickRate !== undefined && (
              <span><span style={{ color: '#888' }}>픽률 </span><b>{value.pickRate.toFixed(1)}%</b></span>
            )}
            {value.advantage && (
              <span><span style={{ color: '#888' }}>유불리 </span><b>{value.advantage}</b></span>
            )}
          </div>
          {value.tips && value.tips.length > 0 && (
            <p style={{ margin: '8px 0 0', color: '#cfd6e6', fontSize: 12, lineHeight: 1.45 }}>
              {value.tips.slice(0, 2).join(' · ')}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}
