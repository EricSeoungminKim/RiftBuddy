import React from 'react'
import { HashRouter, Routes, Route } from 'react-router-dom'
import DraftPage from './pages/DraftPage'
import PostLockInPage from './pages/PostLockInPage'

export default function DraftApp() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<DraftPage />} />
        <Route path="/post-lock-in" element={<PostLockInPage />} />
        <Route path="/postgame" element={<div style={{ color: 'white', padding: 24 }}>Post Game — Screen 3 coming soon</div>} />
      </Routes>
    </HashRouter>
  )
}
