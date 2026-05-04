import React from 'react'
import { championIconUrl } from '../championAssets'

interface Recommendation {
  champion: string
  reason: string
  winRate?: number
  source?: string
}

interface Props {
  recommendations: Recommendation[]
  meta: string[]
  myRole: string
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

export default function DraftRecommendPanel({ recommendations, meta, myRole, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        {myRole} role recommendations
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>Analyzing enemy matchups...</div>}
      {!loading && recommendations.length === 0 && (
        <div style={{ color: '#555', fontSize: 12 }}>Role recommendations will appear during champion select.</div>
      )}
      {recommendations.slice(0, 5).map((rec, i) => (
        <div key={rec.champion} style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 9 }}>
          <span style={{
            width: 18,
            height: 18,
            borderRadius: 4,
            background: i === 0 ? '#f0c040' : '#263858',
            color: i === 0 ? '#0d0e1a' : '#d8e7ff',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 11,
            fontWeight: 800,
            flexShrink: 0,
          }}>{i + 1}</span>
          <img
            src={championIconUrl(rec.champion)}
            alt={rec.champion}
            width={34}
            height={34}
            style={{ borderRadius: 5, border: '1px solid #2a5a8a', objectFit: 'cover', flexShrink: 0 }}
          />
          <div style={{ minWidth: 0 }}>
            <span style={{ color: '#e6edf8', fontWeight: 700, fontSize: 13 }}>{rec.champion}</span>
            {rec.winRate !== undefined && (
              <span style={{ color: '#56f39a', fontWeight: 700, fontSize: 12 }}> {rec.winRate.toFixed(1)}%</span>
            )}
            <span style={{ color: '#aaa', fontSize: 12, lineHeight: 1.45 }}> : {rec.reason}</span>
            {rec.source && <div style={{ color: '#555', fontSize: 10, marginTop: 2 }}>{rec.source}</div>}
          </div>
        </div>
      ))}
      {meta.length > 0 && !loading && (
        <div style={{ marginTop: 8, borderTop: '1px solid #1a1d2e', paddingTop: 8 }}>
          <div style={{ fontSize: 10, color: '#555', marginBottom: 4 }}>OP.GG candidate pool ({meta.length})</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {meta.slice(0, 8).map(c => (
              <span key={c} style={{ fontSize: 11, color: '#666', background: '#1a1d2e', borderRadius: 3, padding: '1px 5px' }}>{c}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
