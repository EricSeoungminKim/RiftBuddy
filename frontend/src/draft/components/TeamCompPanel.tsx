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
  minHeight: 0,
  height: '100%',
  overflowY: 'auto',
}

export default function TeamCompPanel({ strategy, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        Team comp plan
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>Building draft plan...</div>}
      {!loading && !strategy && (
        <div style={{ color: '#555', fontSize: 12 }}>After all 10 picks lock in, RiftBuddy uses the comps and OP.GG matchup evidence to build the fight and macro plan.</div>
      )}
      {strategy && (
        <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc', margin: 0, whiteSpace: 'pre-wrap' }}>
          {strategy.strategy}
        </p>
      )}
    </div>
  )
}
