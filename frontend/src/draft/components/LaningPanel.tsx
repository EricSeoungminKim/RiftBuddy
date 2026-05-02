import React from 'react'
import { MatchupGuide } from '../hooks/useDraftAnalysis'

interface Props {
  matchup: MatchupGuide | null
  loading: boolean
  error: string | null
}

export default function LaningPanel({ matchup, loading, error }: Props) {
  const panelStyle: React.CSSProperties = {
    background: '#12131f',
    border: '1px solid #2a2d4a',
    borderRadius: 8,
    padding: 16,
    color: '#e0e0e0',
    minHeight: 200,
    flex: 1,
  }

  if (loading) return <div style={panelStyle}><span style={{ color: '#888' }}>매치업 분석 중...</span></div>
  if (error) return <div style={panelStyle}><span style={{ color: '#d13a3a' }}>{error}</span></div>
  if (!matchup) return (
    <div style={panelStyle}>
      <span style={{ color: '#555' }}>아군과 적군 챔피언을 선택하면 라이닝 가이드가 표시됩니다</span>
    </div>
  )

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: '0 0 12px', color: '#f0c040', fontSize: 14 }}>
        {matchup.myChampion} vs {matchup.enemyChampion}
      </h3>
      {matchup.advantage && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ color: '#888', fontSize: 12 }}>유불리: </span>
          <span style={{ fontWeight: 'bold' }}>{matchup.advantage}</span>
        </div>
      )}
      {matchup.tips && matchup.tips.length > 0 && (
        <ul style={{ margin: '8px 0 0', paddingLeft: 16, fontSize: 13 }}>
          {matchup.tips.map((tip, i) => (
            <li key={i} style={{ marginBottom: 4, color: '#ccc' }}>{tip}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
