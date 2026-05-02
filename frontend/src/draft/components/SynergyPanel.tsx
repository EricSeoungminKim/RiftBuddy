import React from 'react'
import { TeamStrategy } from '../hooks/useDraftAnalysis'

interface Props {
  strategy: TeamStrategy | null
  loading: boolean
  error: string | null
}

export default function SynergyPanel({ strategy, loading, error }: Props) {
  const panelStyle: React.CSSProperties = {
    background: '#12131f',
    border: '1px solid #2a2d4a',
    borderRadius: 8,
    padding: 16,
    color: '#e0e0e0',
    minHeight: 200,
    flex: 1,
  }

  if (loading) return <div style={panelStyle}><span style={{ color: '#888' }}>팀 전략 생성 중...</span></div>
  if (error) return <div style={panelStyle}><span style={{ color: '#d13a3a' }}>{error}</span></div>
  if (!strategy) return (
    <div style={panelStyle}>
      <span style={{ color: '#555' }}>팀 구성이 완료되면 시너지 전략이 표시됩니다</span>
    </div>
  )

  return (
    <div style={panelStyle}>
      <h3 style={{ margin: '0 0 12px', color: '#f0c040', fontSize: 14 }}>팀 시너지 전략</h3>
      <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc', margin: 0, whiteSpace: 'pre-wrap' }}>
        {strategy.strategy}
      </p>
    </div>
  )
}
