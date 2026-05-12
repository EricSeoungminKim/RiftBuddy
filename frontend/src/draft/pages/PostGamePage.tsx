import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CoachReport, TimelinePoint, usePostGame } from '../hooks/usePostGame'

const panel: React.CSSProperties = {
  background: 'rgba(18, 20, 31, 0.92)',
  border: '1px solid rgba(255,255,255,0.10)',
  borderRadius: 8,
  padding: 16,
  boxShadow: '0 18px 48px rgba(0,0,0,0.25)',
}

const labelStyle: React.CSSProperties = {
  color: '#8f9bb3',
  fontSize: 11,
  textTransform: 'uppercase',
  letterSpacing: 0,
  marginBottom: 6,
}

export default function PostGamePage() {
  const { report, loading, error, fetchReport, clearSnapshots } = usePostGame()
  const navigate = useNavigate()

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  const pageStyle: React.CSSProperties = {
    minHeight: '100vh',
    background: '#080a12',
    color: '#e8edf7',
    fontFamily: 'Avenir Next, Helvetica Neue, sans-serif',
    padding: 24,
    boxSizing: 'border-box',
    overflowY: 'auto',
  }

  return (
    <div style={pageStyle}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, lineHeight: 1.15, color: '#f5c95f' }}>Post-game Coaching Report</h1>
          <p style={{ margin: '7px 0 0', color: '#9aa6bd', fontSize: 13 }}>
            경기 기록은 feedback dashboard로 보여주고, 동시에 다음 게임을 위한 performance seed로 저장됩니다.
          </p>
        </div>
        <button
          onClick={() => { clearSnapshots(); navigate('/') }}
          style={{
            background: '#256fcb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '8px 14px',
            minWidth: 88,
            flexShrink: 0,
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          새 게임 준비
        </button>
      </header>

      {loading && <LoadingState />}
      {error && <ErrorState error={error} />}
      {report && <ReportDashboard report={report} />}
    </div>
  )
}

function LoadingState() {
  return (
    <div style={panel}>
      <div style={labelStyle}>Analyzing match</div>
      <div style={{ fontSize: 18, color: '#fff' }}>코칭 리포트 생성 중...</div>
      <p style={{ color: '#9aa6bd', fontSize: 13, margin: '8px 0 0' }}>
        timeline, CS pace, seed 저장 상태를 정리하고 있습니다.
      </p>
    </div>
  )
}

function ErrorState({ error }: { error: string }) {
  return (
    <div style={{ ...panel, borderColor: 'rgba(255, 109, 109, 0.55)' }}>
      <div style={labelStyle}>Report unavailable</div>
      <div style={{ color: '#ff9a9a', fontSize: 14 }}>{error}</div>
    </div>
  )
}

function ReportDashboard({ report }: { report: CoachReport }) {
  const metrics = report.metrics
  const csDelta = metrics.csVsAvgPct == null ? null : Math.round((metrics.csVsAvgPct - 1) * 100)
  const csDeltaText = csDelta == null ? 'No benchmark' : `${csDelta >= 0 ? '+' : ''}${csDelta}%`

  return (
    <main style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(320px, 100%), 1fr))', gap: 16 }}>
      <section style={{ display: 'grid', gap: 16 }}>
        <div style={{ ...panel, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(150px, 100%), 1fr))', gap: 18, alignItems: 'center' }}>
          <ScoreRing score={metrics.score} />
          <div>
            <div style={labelStyle}>Match summary</div>
            <h2 style={{ margin: 0, fontSize: 22 }}>{metrics.champion} · {metrics.position}</h2>
            <p style={{ margin: '8px 0 0', color: '#9aa6bd', fontSize: 13 }}>
              {metrics.durationMinutes}분 · KDA {metrics.kills}/{metrics.deaths}/{metrics.assists} · {metrics.finalCs} CS
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 14 }}>
              <MetricPill label="CS/min" value={metrics.csPerMinute.toFixed(1)} />
              <MetricPill label="Diamond CS" value={csDeltaText} tone={csDelta != null && csDelta < 0 ? 'warn' : 'good'} />
              <MetricPill label="Avg gold diff" value={`${metrics.avgGoldDiff >= 0 ? '+' : ''}${Math.round(metrics.avgGoldDiff)}`} />
              <MetricPill label="Seed" value={metrics.seedSaved ? 'Saved' : 'Pending'} tone={metrics.seedSaved ? 'good' : 'warn'} />
            </div>
          </div>
        </div>

        <div style={panel}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <div style={labelStyle}>Performance timeline</div>
              <h3 style={{ margin: 0, fontSize: 16 }}>CS and gold flow</h3>
            </div>
            <span style={{ color: '#7f8aa1', fontSize: 12 }}>{metrics.benchmarkSource}</span>
          </div>
          <TimelineChart points={report.timeline} />
        </div>

        <FeedbackSection title="잘한 점" body={report.strengths} />
        <FeedbackSection title="개선할 점" body={report.improvements} accent="#ffb86b" />
      </section>

      <aside style={{ display: 'grid', gap: 16, alignContent: 'start' }}>
        <FeedbackSection title="주요 순간" body={report.moments} />
        <FeedbackSection title="다음 게임 목표" body={report.goals} accent="#7cd992" />
        <div style={panel}>
          <div style={labelStyle}>Stored memory</div>
          <h3 style={{ margin: 0, fontSize: 16 }}>Self-improving loop</h3>
          <p style={{ color: '#aeb8cc', fontSize: 13, lineHeight: 1.6, margin: '10px 0 0' }}>
            이 리포트의 핵심 기록은 ChromaDB performance seed로 저장됩니다. 다음 게임에서는 이 기록이 RAG와 proactive warning에 다시 사용됩니다.
          </p>
          {report.keyMoments.length > 0 && (
            <ul style={{ margin: '12px 0 0', paddingLeft: 18, color: '#d9e1ef', fontSize: 13, lineHeight: 1.55 }}>
              {report.keyMoments.slice(0, 5).map((moment) => <li key={moment}>{moment}</li>)}
            </ul>
          )}
        </div>
      </aside>
    </main>
  )
}

function MetricPill({ label, value, tone = 'neutral' }: { label: string; value: string; tone?: 'neutral' | 'good' | 'warn' }) {
  const color = tone === 'good' ? '#7cd992' : tone === 'warn' ? '#ffb86b' : '#9fc7ff'
  return (
    <div style={{ border: `1px solid ${color}55`, background: `${color}16`, borderRadius: 6, padding: '8px 10px', minWidth: 84 }}>
      <div style={{ color: '#8f9bb3', fontSize: 10 }}>{label}</div>
      <div style={{ color, fontSize: 15, fontWeight: 800, marginTop: 2 }}>{value}</div>
    </div>
  )
}

function ScoreRing({ score }: { score: number }) {
  const radius = 56
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100)
  return (
    <div style={{ width: 150, height: 150, position: 'relative' }}>
      <svg width="150" height="150" viewBox="0 0 150 150">
        <circle cx="75" cy="75" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="12" />
        <circle
          cx="75"
          cy="75"
          r={radius}
          fill="none"
          stroke="#f5c95f"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 75 75)"
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: '#f5c95f', fontSize: 34, fontWeight: 900 }}>{score}</div>
        <div style={{ color: '#9aa6bd', fontSize: 11 }}>Rift score</div>
      </div>
    </div>
  )
}

function TimelineChart({ points }: { points: TimelinePoint[] }) {
  if (!points.length) {
    return <div style={{ color: '#7f8aa1', fontSize: 13 }}>No timeline data recorded.</div>
  }
  const width = 760
  const height = 220
  const maxMinute = Math.max(...points.map(p => p.minute), 1)
  const maxCs = Math.max(...points.map(p => p.cs), 1)
  const maxGoldAbs = Math.max(...points.map(p => Math.abs(p.goldDiff)), 1)
  const csPath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${(p.minute / maxMinute) * width} ${height - (p.cs / maxCs) * (height - 24) - 12}`).join(' ')
  const goldPath = points.map((p, i) => {
    const normalized = (p.goldDiff + maxGoldAbs) / (maxGoldAbs * 2)
    return `${i === 0 ? 'M' : 'L'} ${(p.minute / maxMinute) * width} ${height - normalized * (height - 24) - 12}`
  }).join(' ')

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line x1="0" y1={height - 12} x2={width} y2={height - 12} stroke="rgba(255,255,255,0.12)" />
        <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="rgba(255,255,255,0.08)" strokeDasharray="5 5" />
        <path d={goldPath} fill="none" stroke="#7cd992" strokeWidth="3" strokeLinecap="round" />
        <path d={csPath} fill="none" stroke="#9fc7ff" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <div style={{ display: 'flex', gap: 14, color: '#9aa6bd', fontSize: 12 }}>
        <span><span style={{ color: '#9fc7ff' }}>●</span> CS</span>
        <span><span style={{ color: '#7cd992' }}>●</span> Gold diff</span>
      </div>
    </div>
  )
}

function FeedbackSection({ title, body, accent = '#9fc7ff' }: { title: string; body: string; accent?: string }) {
  return (
    <section style={{ ...panel, borderLeft: `3px solid ${accent}` }}>
      <div style={labelStyle}>Coach feedback</div>
      <h3 style={{ margin: 0, color: accent, fontSize: 16 }}>{title}</h3>
      <p style={{ color: '#d7deeb', fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: '10px 0 0' }}>
        {body || '분석 결과가 충분하지 않습니다. 다음 게임에서는 더 많은 snapshot을 기록해보세요.'}
      </p>
    </section>
  )
}
