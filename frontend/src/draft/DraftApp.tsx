import React, { useEffect } from 'react'
import { HashRouter, Routes, Route, useNavigate } from 'react-router-dom'
import DraftPage from './pages/DraftPage'
import PostLockInPage from './pages/PostLockInPage'
import PostGamePage from './pages/PostGamePage'

function GameEndListener() {
  const navigate = useNavigate()

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8765/ws')
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'game_end') {
          navigate('/postgame')
        }
      } catch {
        // non-JSON messages (plain text advice) — ignore
      }
    }
    return () => ws.close()
  }, [navigate])

  return null
}

export default function DraftApp() {
  return (
    <HashRouter>
      <GameEndListener />
      <Routes>
        <Route path="/" element={<DraftPage />} />
        <Route path="/post-lock-in" element={<PostLockInPage />} />
        <Route path="/postgame" element={<PostGamePage />} />
      </Routes>
    </HashRouter>
  )
}
