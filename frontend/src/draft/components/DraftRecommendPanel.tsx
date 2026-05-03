import React from 'react'

interface Recommendation {
  champion: string
  reason: string
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
}

export default function DraftRecommendPanel({ recommendations, meta, myRole, loading }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        {myRole} 추천 픽
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>분석 중...</div>}
      {!loading && recommendations.length === 0 && (
        <div style={{ color: '#555', fontSize: 12 }}>챔피언 선택 진행 중 자동 추천됩니다</div>
      )}
      {recommendations.map((rec, i) => (
        <div key={rec.champion} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              background: i === 0 ? '#f0c040' : '#3a8fd1',
              color: '#0d0e1a',
              borderRadius: 4,
              padding: '1px 7px',
              fontSize: 11,
              fontWeight: 700,
            }}>{i + 1}</span>
            <span style={{ color: '#e0e0e0', fontWeight: 600, fontSize: 14 }}>{rec.champion}</span>
          </div>
          <div style={{ color: '#aaa', fontSize: 12, marginTop: 4, lineHeight: 1.5, paddingLeft: 4 }}>{rec.reason}</div>
        </div>
      ))}
      {meta.length > 0 && !loading && (
        <div style={{ marginTop: 8, borderTop: '1px solid #1a1d2e', paddingTop: 8 }}>
          <div style={{ fontSize: 10, color: '#555', marginBottom: 4 }}>메타 티어 ({meta.length})</div>
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
