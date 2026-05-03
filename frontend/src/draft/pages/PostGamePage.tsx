import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePostGame } from '../hooks/usePostGame'

export default function PostGamePage() {
  const { report, loading, error, fetchReport, clearSnapshots } = usePostGame()
  const navigate = useNavigate()

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

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
    overflowY: 'auto',
  }

  const cardStyle: React.CSSProperties = {
    background: '#12131f',
    border: '1px solid #2a2d4a',
    borderRadius: 8,
    padding: 16,
  }

  const headingStyle: React.CSSProperties = {
    margin: '0 0 10px',
    fontSize: 14,
    color: '#f0c040',
  }

  const textStyle: React.CSSProperties = {
    fontSize: 13,
    lineHeight: 1.7,
    color: '#ccc',
    margin: 0,
    whiteSpace: 'pre-wrap',
  }

  return (
    <div style={pageStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 16, color: '#f0c040' }}>RiftBuddy — 게임 코칭 리포트</h2>
        <button
          onClick={clearSnapshots}
          style={{ background: '#2a2d4a', color: '#aaa', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }}
        >
          초기화
        </button>
      </div>

      {loading && (
        <div style={cardStyle}>
          <span style={{ color: '#888' }}>코칭 리포트 생성 중... (10-20초 소요)</span>
        </div>
      )}

      {error && (
        <div style={{ ...cardStyle, borderColor: '#d13a3a' }}>
          <span style={{ color: '#d13a3a' }}>{error}</span>
        </div>
      )}

      {report && (
        <>
          <div style={cardStyle}>
            <h3 style={headingStyle}>잘한 점</h3>
            <p style={textStyle}>{report.strengths}</p>
          </div>
          <div style={cardStyle}>
            <h3 style={headingStyle}>개선할 점</h3>
            <p style={textStyle}>{report.improvements}</p>
          </div>
          <div style={cardStyle}>
            <h3 style={headingStyle}>주요 순간</h3>
            <p style={textStyle}>{report.moments}</p>
          </div>
          <div style={cardStyle}>
            <h3 style={headingStyle}>다음 게임 목표</h3>
            <p style={textStyle}>{report.goals}</p>
          </div>
        </>
      )}

      {!loading && !error && !report && (
        <div style={cardStyle}>
          <span style={{ color: '#555' }}>게임이 끝나면 코칭 리포트가 자동으로 표시됩니다</span>
        </div>
      )}

      <button
        onClick={() => { clearSnapshots(); navigate('/') }}
        style={{ background: '#3a8fd1', color: '#fff', border: 'none', borderRadius: 4, padding: '6px 18px', cursor: 'pointer', fontSize: 13, marginTop: 16, alignSelf: 'flex-start' }}
      >
        새 게임 시작
      </button>
    </div>
  )
}
