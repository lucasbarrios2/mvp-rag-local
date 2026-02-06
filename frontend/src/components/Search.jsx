import { useState } from 'react'
import { search, videoContext } from '../api'

function scoreColor(score) {
  if (score >= 0.8) return 'var(--green)'
  if (score >= 0.5) return 'var(--yellow)'
  return 'var(--red)'
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showFilters, setShowFilters] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [detailData, setDetailData] = useState({})
  const [detailLoading, setDetailLoading] = useState({})
  const [filters, setFilters] = useState({
    category: '',
    emotional_tone: '',
    intensity_min: '',
    intensity_max: '',
    viral_potential_min: '',
    viral_potential_max: '',
    camera_type: '',
    compilation_theme: '',
    standalone_score_min: '',
    standalone_score_max: '',
    visual_quality_score_min: '',
    visual_quality_score_max: '',
  })

  async function handleSearch(e) {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const f = {}
      if (filters.category) f.category = filters.category
      if (filters.emotional_tone) f.emotional_tone = filters.emotional_tone
      if (filters.intensity_min) f.intensity_min = parseFloat(filters.intensity_min)
      if (filters.intensity_max) f.intensity_max = parseFloat(filters.intensity_max)
      if (filters.viral_potential_min) f.viral_potential_min = parseFloat(filters.viral_potential_min)
      if (filters.viral_potential_max) f.viral_potential_max = parseFloat(filters.viral_potential_max)
      if (filters.camera_type) f.camera_type = filters.camera_type
      if (filters.compilation_theme) f.compilation_theme = filters.compilation_theme
      if (filters.standalone_score_min) f.standalone_score_min = parseFloat(filters.standalone_score_min)
      if (filters.standalone_score_max) f.standalone_score_max = parseFloat(filters.standalone_score_max)
      if (filters.visual_quality_score_min) f.visual_quality_score_min = parseFloat(filters.visual_quality_score_min)
      if (filters.visual_quality_score_max) f.visual_quality_score_max = parseFloat(filters.visual_quality_score_max)
      const res = await search(query, f)
      setResults(res)
      setExpandedId(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function toggleExpand(id) {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    setExpandedId(id)
    if (!detailData[id]) {
      setDetailLoading(prev => ({ ...prev, [id]: true }))
      try {
        const ctx = await videoContext(id)
        setDetailData(prev => ({ ...prev, [id]: ctx }))
      } catch {
        // silently fail
      } finally {
        setDetailLoading(prev => ({ ...prev, [id]: false }))
      }
    }
  }

  function updateFilter(key, value) {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div>
      <h2>Search</h2>

      <form onSubmit={handleSearch} className="search-bar">
        <input
          type="text"
          placeholder="Search videos semantically..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="btn" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      <button
        className="filters-toggle"
        onClick={() => setShowFilters(!showFilters)}
      >
        {showFilters ? '\u25BC' : '\u25B6'} Filters
      </button>

      {showFilters && (
        <div className="filters-panel">
          <div className="filter-group">
            <label>Category</label>
            <input
              type="text"
              placeholder="e.g. News"
              value={filters.category}
              onChange={(e) => updateFilter('category', e.target.value)}
            />
          </div>
          <div className="filter-group">
            <label>Emotional Tone</label>
            <input
              type="text"
              placeholder="e.g. dramatic"
              value={filters.emotional_tone}
              onChange={(e) => updateFilter('emotional_tone', e.target.value)}
            />
          </div>
          <div className="filter-group">
            <label>Intensity Range</label>
            <div className="filter-row">
              <input
                type="number"
                placeholder="Min"
                min="0"
                max="10"
                step="0.1"
                value={filters.intensity_min}
                onChange={(e) => updateFilter('intensity_min', e.target.value)}
              />
              <input
                type="number"
                placeholder="Max"
                min="0"
                max="10"
                step="0.1"
                value={filters.intensity_max}
                onChange={(e) => updateFilter('intensity_max', e.target.value)}
              />
            </div>
          </div>
          <div className="filter-group">
            <label>Viral Potential Range</label>
            <div className="filter-row">
              <input
                type="number"
                placeholder="Min"
                min="0"
                max="10"
                step="0.1"
                value={filters.viral_potential_min}
                onChange={(e) => updateFilter('viral_potential_min', e.target.value)}
              />
              <input
                type="number"
                placeholder="Max"
                min="0"
                max="10"
                step="0.1"
                value={filters.viral_potential_max}
                onChange={(e) => updateFilter('viral_potential_max', e.target.value)}
              />
            </div>
          </div>

          <div className="section-title" style={{ marginTop: 12 }}>Compilation Filters</div>
          <div className="filter-group">
            <label>Camera Type</label>
            <select value={filters.camera_type} onChange={(e) => updateFilter('camera_type', e.target.value)}>
              <option value="">All</option>
              <option value="cctv">CCTV</option>
              <option value="dashcam">Dashcam</option>
              <option value="cellphone">Cellphone</option>
              <option value="drone">Drone</option>
              <option value="bodycam">Bodycam</option>
              <option value="gopro">GoPro</option>
              <option value="professional">Professional</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="filter-group">
            <label>Compilation Theme</label>
            <input
              type="text"
              placeholder="e.g. animais_em_cidades"
              value={filters.compilation_theme}
              onChange={(e) => updateFilter('compilation_theme', e.target.value)}
            />
          </div>
          <div className="filter-group">
            <label>Standalone Score Range</label>
            <div className="filter-row">
              <input type="number" placeholder="Min" min="0" max="10" step="0.1" value={filters.standalone_score_min} onChange={(e) => updateFilter('standalone_score_min', e.target.value)} />
              <input type="number" placeholder="Max" min="0" max="10" step="0.1" value={filters.standalone_score_max} onChange={(e) => updateFilter('standalone_score_max', e.target.value)} />
            </div>
          </div>
          <div className="filter-group">
            <label>Visual Quality Range</label>
            <div className="filter-row">
              <input type="number" placeholder="Min" min="0" max="10" step="0.1" value={filters.visual_quality_score_min} onChange={(e) => updateFilter('visual_quality_score_min', e.target.value)} />
              <input type="number" placeholder="Max" min="0" max="10" step="0.1" value={filters.visual_quality_score_max} onChange={(e) => updateFilter('visual_quality_score_max', e.target.value)} />
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      {results && (
        <>
          <div className="text-muted text-sm mb-16">
            {results.total_results} result{results.total_results !== 1 ? 's' : ''} for "{results.query}"
          </div>
          <div className="results-list">
            {results.results.map((r) => (
              <div key={r.id}>
                <div className="result-card" onClick={() => toggleExpand(r.id)}>
                  <div className="result-header">
                    <span className="filename">{r.filename || `Video #${r.id}`}</span>
                    <span className="video-id">ID: {r.id}</span>
                  </div>
                  {r.event_headline && (
                    <div className="event-headline" style={{ fontSize: '0.85em', color: 'var(--text-muted)', marginBottom: 4 }}>
                      {r.event_headline}
                    </div>
                  )}
                  <div className="score-bar">
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${(r.score * 100).toFixed(0)}%`,
                        background: scoreColor(r.score),
                      }}
                    />
                  </div>
                  <div className="badges">
                    <span className="badge">Score: {r.score.toFixed(3)}</span>
                    {r.emotional_tone && <span className="badge tone">{r.emotional_tone}</span>}
                    {r.intensity != null && <span className="badge intensity">Int: {r.intensity}</span>}
                    {r.viral_potential != null && <span className="badge viral">Viral: {r.viral_potential}</span>}
                    {r.is_exclusive && <span className="badge exclusive">Exclusive</span>}
                    {r.category && <span className="badge category">{r.category}</span>}
                    {r.source && <span className="badge">{r.source}</span>}
                    {r.camera_type && <span className="badge">{r.camera_type}</span>}
                    {r.standalone_score != null && <span className="badge">Solo: {r.standalone_score}</span>}
                    {r.visual_quality_score != null && <span className="badge">VQ: {r.visual_quality_score}</span>}
                  </div>
                </div>
                {expandedId === r.id && (
                  <ExpandedDetail data={detailData[r.id]} loading={detailLoading[r.id]} />
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {results && results.total_results === 0 && (
        <div className="empty">No results found. Try a different query.</div>
      )}
    </div>
  )
}

function ExpandedDetail({ data, loading }) {
  if (loading) return <div className="loading"><span className="spinner" /> Loading details...</div>
  if (!data) return null

  return (
    <div className="card" style={{ marginTop: 4, marginBottom: 8 }}>
      {data.visual_description && (
        <div className="detail-field">
          <div className="field-label">Visual Description</div>
          <div className="field-value">{data.visual_description}</div>
        </div>
      )}
      {data.narrative_description && (
        <div className="detail-field">
          <div className="field-label">Narrative Description</div>
          <div className="field-value">{data.narrative_description}</div>
        </div>
      )}
      {data.visual_tags?.length > 0 && (
        <div className="detail-field">
          <div className="field-label">Tags</div>
          <div className="tags-list">
            {data.visual_tags.map((t, i) => <span key={i} className="tag">{t}</span>)}
          </div>
        </div>
      )}
      {data.themes && Object.keys(data.themes).length > 0 && (
        <div className="detail-field">
          <div className="field-label">Themes</div>
          <div className="themes-grid">
            {Object.entries(data.themes).map(([name, score]) => (
              <div key={name} className="theme-row">
                <span className="theme-name">{name}</span>
                <div className="theme-bar">
                  <div className="theme-fill" style={{ width: `${(score * 100).toFixed(0)}%` }} />
                </div>
                <span className="theme-score">{typeof score === 'number' ? score.toFixed(2) : score}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
