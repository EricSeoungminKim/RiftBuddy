import React, { useState } from 'react'

const DDRAGON_VERSION = '14.9.1'
const DDRAGON_BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img/champion`

function championIconUrl(championId: string): string {
  // DDragon expects PascalCase champion IDs e.g. "Ahri", "DrMundo", "Kaisa"
  return `${DDRAGON_BASE}/${championId}.png`
}

interface ChampionSlotProps {
  championId?: string   // e.g. "Ahri", "Zed". undefined = empty slot
  role?: string         // display label below icon
  isAlly?: boolean      // blue = ally, red = enemy
  size?: number         // px, default 64
  onClick?: () => void
  selected?: boolean    // highlight ring
}

export default function ChampionSlot({
  championId,
  role,
  isAlly = true,
  size = 64,
  onClick,
  selected = false,
}: ChampionSlotProps) {
  const [imgError, setImgError] = useState(false)

  const borderColor = selected
    ? '#f0c040'
    : isAlly
    ? '#3a8fd1'
    : '#d13a3a'

  const containerStyle: React.CSSProperties = {
    width: size,
    height: size + (role ? 20 : 0),
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    cursor: onClick ? 'pointer' : 'default',
  }

  const iconStyle: React.CSSProperties = {
    width: size,
    height: size,
    borderRadius: 4,
    border: `2px solid ${borderColor}`,
    overflow: 'hidden',
    background: '#1a1a2e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  }

  const placeholderStyle: React.CSSProperties = {
    ...iconStyle,
    border: `2px dashed ${isAlly ? '#2a5a8a' : '#8a2a2a'}`,
    color: isAlly ? '#3a8fd1' : '#d13a3a',
    fontSize: 24,
    userSelect: 'none',
  }

  return (
    <div style={containerStyle} onClick={onClick}>
      {championId && !imgError ? (
        <div style={iconStyle}>
          <img
            src={championIconUrl(championId)}
            alt={championId}
            width={size}
            height={size}
            style={{ objectFit: 'cover' }}
            onError={() => setImgError(true)}
          />
        </div>
      ) : (
        <div style={placeholderStyle}>?</div>
      )}
      {role && (
        <span style={{ fontSize: 11, color: '#aaa', marginTop: 2, textAlign: 'center' }}>
          {role}
        </span>
      )}
    </div>
  )
}
