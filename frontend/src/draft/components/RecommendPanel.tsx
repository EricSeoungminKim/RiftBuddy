import React from 'react'
import { ChampionAnalysis } from '../hooks/useDraftAnalysis'

interface Props {
  analysis: ChampionAnalysis | null
  loading: boolean
  error: string | null
}

export default function RecommendPanel({ analysis, loading, error }: Props) {
  const panelStyle: React.CSSProperties = {
    background: '#12131f',
    border: '1px solid #2a2d4a',
    borderRadius: 8,
    padding: 16,
    color: '#e0e0e0',
    minHeight: 200,
    flex: 1,
  }

  if (loading) return <div style={panelStyle}><span style={{ color: '#888' }}>분석 중...</span></div>
  if (error) return <div style={panelStyle}><span style={{ color: '#d13a3a' }}>{error}</span></div>
  if (!analysis) return (
    <div style={panelStyle}>
      <span style={{ color: '#555' }}>챔피언을 선택하면 추천 분석이 표시됩니다</span>
    </div>
  )

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: '0 0 12px', color: '#f0c040', fontSize: 14 }}>
        {analysis.champion} — {analysis.role}
      </h3>
      {analysis.tier && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ color: '#888', fontSize: 12 }}>티어: </span>
          <span style={{ fontWeight: 'bold' }}>{analysis.tier}</span>
        </div>
      )}
      {analysis.winRate !== undefined && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ color: '#888', fontSize: 12 }}>승률: </span>
          <span style={{ fontWeight: 'bold' }}>{(analysis.winRate * 100).toFixed(1)}%</span>
        </div>
      )}
      {analysis.tips && analysis.tips.length > 0 && (
        <ul style={{ margin: '8px 0 0', paddingLeft: 16, fontSize: 13 }}>
          {analysis.tips.map((tip, i) => (
            <li key={i} style={{ marginBottom: 4, color: '#ccc' }}>{tip}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
