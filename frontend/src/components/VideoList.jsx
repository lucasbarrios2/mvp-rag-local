import { useState, useEffect } from 'react'
import { search, videoContext, similar } from '../api'
import VideoDetail from './VideoDetail'

export default function VideoList() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [similarResults, setSimilarResults] = useState(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    loadVideos()
  }, [])

  async function loadVideos() {
    setLoading(true)
    setError(null)
    try {
      // Use a broad search to list videos since there's no dedicated list endpoint
      const res = await search('video', {}, 50)
      setVideos(res.results)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function filterVideos(e) {
    e?.preventDefault()
    if (!query.trim()) {
      loadVideos()
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await search(query, {}, 50)
      setVideos(res.results)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function selectVideo(id) {
    if (selectedId === id) {
      setSelectedId(null)
      setDetail(null)
      setSimilarResults(null)
      return
    }
    setSelectedId(id)
    setDetailLoading(true)
    setSimilarResults(null)
    try {
      const ctx = await videoContext(id)
      setDetail(ctx)
    } catch (e) {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  async function findSimilar() {
    if (!selectedId) return
    try {
      const res = await similar(selectedId)
      setSimilarResults(res)
    } catch {
      // silently fail
    }
  }

  if (loading && videos.length === 0) {
    return <div className="loading"><span className="spinner" /> Loading videos...</div>
  }

  return (
    <div>
      <h2>Videos</h2>

      <form onSubmit={filterVideos} className="search-bar">
        <input
          type="text"
          placeholder="Filter videos..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className="btn btn-sm">Filter</button>
        <button type="button" className="btn btn-sm btn-outline" onClick={loadVideos}>All</button>
      </form>

      {error && <div className="error-msg">{error}</div>}

      <div className="video-detail-layout">
        <div>
          <div className="video-list">
            {videos.map(v => (
              <div
                key={v.id}
                className={`video-row ${selectedId === v.id ? 'selected' : ''}`}
                onClick={() => selectVideo(v.id)}
              >
                <span className="filename">{v.filename || `Video #${v.id}`}</span>
                {v.emotional_tone && <span className="badge tone">{v.emotional_tone}</span>}
                {v.source && <span className="badge">{v.source}</span>}
              </div>
            ))}
          </div>

          {videos.length === 0 && !loading && (
            <div className="empty">No videos found.</div>
          )}
        </div>

        <div>
          {detailLoading && (
            <div className="loading"><span className="spinner" /> Loading details...</div>
          )}

          {detail && !detailLoading && (
            <VideoDetail
              video={detail}
              onFindSimilar={findSimilar}
              onDeleted={(id) => {
                setVideos(prev => prev.filter(v => v.id !== id))
                setSelectedId(null)
                setDetail(null)
                setSimilarResults(null)
              }}
            />
          )}

          {!detail && !detailLoading && (
            <div className="empty">Select a video to view details</div>
          )}

          {similarResults && similarResults.results.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div className="section-title">Similar Videos</div>
              <div className="results-list">
                {similarResults.results.map(r => (
                  <div
                    key={r.id}
                    className="result-card"
                    onClick={() => selectVideo(r.id)}
                  >
                    <div className="result-header">
                      <span className="filename">{r.filename || `Video #${r.id}`}</span>
                      <span className="badge">Score: {r.score.toFixed(3)}</span>
                    </div>
                    <div className="badges">
                      {r.emotional_tone && <span className="badge tone">{r.emotional_tone}</span>}
                      {r.category && <span className="badge category">{r.category}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
