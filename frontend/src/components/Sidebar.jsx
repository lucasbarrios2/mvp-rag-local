import { useState, useEffect } from 'react'
import { health } from '../api'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '\u25A6' },
  { id: 'search', label: 'Search', icon: '\u2315' },
  { id: 'rag', label: 'RAG Chat', icon: '\u2601' },
  { id: 'ingest', label: 'Ingest', icon: '\u2B06' },
  { id: 'videos', label: 'Videos', icon: '\u25B6' },
]

export default function Sidebar({ active, onNavigate }) {
  const [apiOk, setApiOk] = useState(false)
  const [apiKey, setApiKey] = useState(localStorage.getItem('rag_api_key') || '')
  const [keyInput, setKeyInput] = useState(apiKey)

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 15000)
    return () => clearInterval(interval)
  }, [])

  async function checkHealth() {
    try {
      await health()
      setApiOk(true)
    } catch {
      setApiOk(false)
    }
  }

  function saveKey() {
    localStorage.setItem('rag_api_key', keyInput)
    setApiKey(keyInput)
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>MENTOR</h1>
        <p>RAG Client</p>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={active === item.id ? 'active' : ''}
            onClick={() => onNavigate(item.id)}
          >
            <span className="icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="api-key-input">
          <input
            type="password"
            placeholder="API Key"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && saveKey()}
          />
          <button onClick={saveKey}>Set</button>
        </div>
        <div className="api-status">
          <span className={`dot ${apiOk ? 'ok' : ''}`} />
          API: {apiOk ? 'Connected' : 'Offline'}
        </div>
      </div>
    </div>
  )
}
