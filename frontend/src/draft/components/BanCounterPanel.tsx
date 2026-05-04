import React from 'react'
import { BanCounter } from '../hooks/useDraftAnalysis'
import { championIconUrl } from '../championAssets'

interface Props {
  target: string
  counters: BanCounter[]
  loading: boolean
}

const cardStyle: React.CSSProperties = {
  background: '#12131f',
  border: '1px solid #2a2d4a',
  borderRadius: 8,
  padding: 14,
  minWidth: 0,
  overflowY: 'auto',
}

export default function BanCounterPanel({ target, counters, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        Ban recommendations {target ? `vs ${target}` : ''}
      </div>
      {!target && loading && <div style={{ color: '#888', fontSize: 12 }}>Loading OP.GG role-meta bans...</div>}
      {!target && !loading && counters.length === 0 && <div style={{ color: '#555', fontSize: 12 }}>Hover or select a champion to add counter-ban analysis.</div>}
      {target && loading && <div style={{ color: '#888', fontSize: 12 }}>Loading OP.GG counter data...</div>}
      {target && !loading && counters.length === 0 && <div style={{ color: '#555', fontSize: 12 }}>No ban data available from OP.GG.</div>}
      {counters.slice(0, 5).map((counter, index) => (
        <div key={counter.champion} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9 }}>
          <span style={{ color: '#f0c040', fontWeight: 800, fontSize: 12, width: 14 }}>{index + 1}</span>
          <img
            src={championIconUrl(counter.champion)}
            alt={counter.champion}
            width={32}
            height={32}
            style={{ borderRadius: 5, border: '1px solid #8a2a2a', objectFit: 'cover', flexShrink: 0 }}
          />
          <div style={{ minWidth: 0 }}>
            <span style={{ color: '#ff7676', fontWeight: 700, fontSize: 13 }}>{counter.champion}</span>
            {counter.winRate !== undefined && (
              <span style={{ color: '#f0c040', fontWeight: 700, fontSize: 12 }}> {counter.winRate.toFixed(1)}%</span>
            )}
            <span style={{ color: '#aaa', fontSize: 12 }}> : {counter.reason}</span>
            <div style={{ color: '#555', fontSize: 10, marginTop: 2 }}>{counter.source}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
