import React from 'react'
import { MatchupGuide } from '../hooks/useDraftAnalysis'

interface Props {
  recommendedChampion: string
  enemyChampions: string[]
  matchups: Record<number, MatchupGuide>
  loading: boolean
  myRole: string
}

const cardStyle: React.CSSProperties = {
  background: '#12131f',
  border: '1px solid #2a2d4a',
  borderRadius: 8,
  padding: 14,
  flex: 1,
  minWidth: 0,
}

function winRateColor(wr: number | undefined): string {
  if (wr === undefined) return '#888'
  if (wr >= 52) return '#56f39a'
  if (wr <= 47) return '#f35656'
  return '#f0c040'
}

export default function OpponentMatchupPanel({ recommendedChampion, enemyChampions, matchups, loading, myRole: _myRole }: Props) {
  const filled = enemyChampions.filter(Boolean)
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
        상대 챔피언 승률 {recommendedChampion ? `vs ${recommendedChampion}` : ''}
      </div>
      {loading && <div style={{ color: '#888', fontSize: 12 }}>불러오는 중...</div>}
      {!loading && filled.length === 0 && (
        <div style={{ color: '#555', fontSize: 12 }}>상대 챔피언이 픽되면 승률이 표시됩니다</div>
      )}
      {filled.map((enemy) => {
        const matchup = Object.values(matchups).find(m => m.enemyChampion === enemy)
        const wr = matchup?.winRate
        return (
          <div key={enemy} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ color: '#e05050', fontSize: 13 }}>{enemy}</span>
            <span style={{ color: winRateColor(wr), fontWeight: 700, fontSize: 14 }}>
              {wr !== undefined ? `${wr.toFixed(1)}%` : loading ? '...' : 'N/A'}
            </span>
          </div>
        )
      })}
    </div>
  )
}
