import { useState, useEffect } from 'react'
import { stats } from '../api'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadStats()
  }, [])

  async function loadStats() {
    setLoading(true)
    setError(null)
    try {
      const s = await stats()
      setData(s)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading"><span className="spinner" /> Loading stats...</div>
  if (error) return <div className="error-msg">{error}</div>
  if (!data) return null

  const total = data.videos_total || 1
  const pipeline = [
    { key: 'pending', label: 'Pending', count: data.videos_pending },
    { key: 'analyzing', label: 'Analyzing', count: (data.videos_total - data.videos_analyzed - data.videos_pending - data.videos_failed) },
    { key: 'analyzed', label: 'Analyzed', count: data.videos_analyzed },
    { key: 'failed', label: 'Failed', count: data.videos_failed },
  ].filter(s => s.count > 0)

  return (
    <div>
      <h2>Dashboard</h2>

      <div className="cards-grid">
        <StatCard value={data.videos_total} label="Total Videos" />
        <StatCard value={data.videos_analyzed} label="Analyzed" />
        <StatCard value={data.videos_pending} label="Pending" />
        <StatCard value={data.videos_failed} label="Failed" />
        <StatCard value={data.videos_with_metadata} label="With Metadata" />
        <StatCard value={data.videos_with_unified_embedding} label="Embeddings" />
      </div>

      <div className="section-title">Processing Pipeline</div>
      <div className="pipeline">
        {pipeline.map(s => (
          <div
            key={s.key}
            className={`pipeline-segment ${s.key}`}
            style={{ flex: s.count }}
          >
            {s.label} ({s.count})
          </div>
        ))}
      </div>

      <div className="section-title">Queue</div>
      <div className="cards-grid">
        <StatCard value={data.queue_pending} label="Queue Pending" />
        <StatCard value={data.queue_processing} label="Processing" />
        <StatCard value={data.queue_completed} label="Completed" />
        <StatCard value={data.queue_failed} label="Queue Failed" />
      </div>

      {data.qdrant_collections && (
        <>
          <div className="section-title mt-12">Qdrant Collections</div>
          <div className="collections-grid">
            {Object.entries(data.qdrant_collections).map(([name, info]) => (
              <div key={name} className="collection-card">
                <div className="name">{name}</div>
                <div className="count">{info?.point_count ?? '?'}</div>
                <div className="count-label">vectors</div>
              </div>
            ))}
          </div>
        </>
      )}

      <button className="btn btn-outline btn-sm mt-12" onClick={loadStats}>
        Refresh
      </button>
    </div>
  )
}

function StatCard({ value, label }) {
  return (
    <div className="stat-card">
      <div className="value">{value ?? 0}</div>
      <div className="label">{label}</div>
    </div>
  )
}
