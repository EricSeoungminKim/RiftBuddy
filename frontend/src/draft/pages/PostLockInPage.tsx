import React, { useState } from 'react'
import { useDraftAnalysis } from '../hooks/useDraftAnalysis'

const ROLES = ['탑', '정글', '미드', '바텀', '서폿']

export default function PostLockInPage() {
  const [champion, setChampion] = useState('')
  const [role, setRole] = useState('미드')
  const [applyStatus, setApplyStatus] = useState<string | null>(null)

  const { runes, teamStrategy, loading, error, fetchRunes, applyRunes } = useDraftAnalysis()

  const handleFetchRunes = () => {
    if (!champion.trim()) return
    fetchRunes(champion.trim(), role)
  }

  const handleApplyRunes = async () => {
    if (!runes) return
    setApplyStatus('적용 중...')
    const result = await applyRunes(runes)
    if (result?.success) {
      setApplyStatus(`✓ ${result.message}`)
    } else {
      setApplyStatus('룬 적용 실패 — League 클라이언트가 열려 있는지 확인하세요')
    }
  }

  const pageStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#0d0e1a',
    color: '#e0e0e0',
    fontFamily: 'sans-serif',
    padding: 16,
    boxSizing: 'border-box',
    gap: 16,
  }

  const cardStyle: React.CSSProperties = {
    background: '#12131f',
    border: '1px solid #2a2d4a',
    borderRadius: 8,
    padding: 16,
  }

  const pillStyle: React.CSSProperties = {
    display: 'inline-block',
    background: '#1a2a3a',
    border: '1px solid #3a8fd1',
    borderRadius: 12,
    padding: '2px 10px',
    fontSize: 12,
    color: '#aaddff',
    margin: '2px 4px 2px 0',
  }

  return (
    <div style={pageStyle}>
      <h2 style={{ margin: 0, fontSize: 16, color: '#f0c040' }}>RiftBuddy — 챔피언 확정 후</h2>

      {/* Champion + role selector */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          value={champion}
          onChange={e => setChampion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleFetchRunes()}
          placeholder="내 챔피언 (e.g. Ahri)"
          style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #3a8fd1', borderRadius: 4, padding: '4px 8px', fontSize: 13, width: 160 }}
        />
        <select
          value={role}
          onChange={e => setRole(e.target.value)}
          style={{ background: '#1a1a2e', color: '#e0e0e0', border: '1px solid #2a2d4a', borderRadius: 4, padding: '4px 8px', fontSize: 13 }}
        >
          {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <button
          onClick={handleFetchRunes}
          disabled={!champion.trim() || loading}
          style={{ background: '#3a8fd1', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 14px', cursor: 'pointer', fontSize: 13 }}
        >
          룬 추천
        </button>
      </div>

      {/* Rune recommendation */}
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#f0c040' }}>추천 룬</h3>
        {loading && <span style={{ color: '#888' }}>불러오는 중...</span>}
        {error && <span style={{ color: '#d13a3a' }}>{error}</span>}
        {!loading && !error && !runes && (
          <span style={{ color: '#555' }}>챔피언과 역할을 입력하면 룬 추천이 표시됩니다</span>
        )}
        {runes && (
          <>
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: '#888', fontSize: 12 }}>룬 페이지 이름: </span>
              <span style={{ fontWeight: 'bold' }}>{runes.name}</span>
            </div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: '#888', fontSize: 12 }}>주 특성: </span>
              <span>{runes.primaryStyleId}</span>
              <span style={{ color: '#888', fontSize: 12, marginLeft: 16 }}>보조 특성: </span>
              <span>{runes.subStyleId}</span>
            </div>
            <div style={{ marginBottom: 12 }}>
              <span style={{ color: '#888', fontSize: 12, display: 'block', marginBottom: 4 }}>선택 룬:</span>
              {runes.selectedPerkIds.map(id => (
                <span key={id} style={pillStyle}>{id}</span>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <button
                onClick={handleApplyRunes}
                style={{ background: '#f0c040', color: '#0d0e1a', border: 'none', borderRadius: 4, padding: '6px 18px', cursor: 'pointer', fontWeight: 'bold', fontSize: 13 }}
              >
                룬 자동 적용
              </button>
              {applyStatus && (
                <span style={{ fontSize: 13, color: applyStatus.startsWith('✓') ? '#4caf50' : '#d13a3a' }}>
                  {applyStatus}
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* Team strategy (carried over from Screen 1 if available) */}
      {teamStrategy && (
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#f0c040' }}>팀 전략 요약</h3>
          <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc', margin: 0, whiteSpace: 'pre-wrap' }}>
            {teamStrategy.strategy}
          </p>
        </div>
      )}
    </div>
  )
}
