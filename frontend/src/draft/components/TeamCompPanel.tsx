import React from 'react'
import { TeamStrategy } from '../hooks/useDraftAnalysis'

interface Props {
  strategy: TeamStrategy | null
  loading: boolean
}

const cardStyle: React.CSSProperties = {
  background: '#12131f',
  border: '1px solid #2a2d4a',
  borderRadius: 8,
  padding: 14,
  flex: 1,
  minWidth: 0,
  overflowY: 'auto',
  maxHeight: 280,
}

export default function TeamCompPanel({ strategy, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        팀 조합 분석
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>분석 중...</div>}
      {!loading && !strategy && (
        <div style={{ color: '#555', fontSize: 12 }}>아군 챔피언이 2명 이상 선택되면 자동으로 팀 시너지를 분석합니다</div>
      )}
      {strategy && (
        <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc', margin: 0, whiteSpace: 'pre-wrap' }}>
          {strategy.strategy}
        </p>
      )}
    </div>
  )
}
