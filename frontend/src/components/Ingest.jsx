import { useState, useRef } from 'react'
import { ingest } from '../api'

const INITIAL_META = {
  newsflare_id: '',
  title: '',
  description: '',
  uploader: '',
  filming_location: '',
  is_exclusive: false,
  category: '',
  tags: '',
}

export default function Ingest() {
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [meta, setMeta] = useState({ ...INITIAL_META })
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const fileRef = useRef()

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f && f.type.startsWith('video/')) {
      setFile(f)
    }
  }

  function handleFileSelect(e) {
    const f = e.target.files[0]
    if (f) setFile(f)
  }

  function updateMeta(key, value) {
    setMeta(prev => ({ ...prev, [key]: value }))
  }

  async function handleIngest() {
    if (!file) return
    setLoading(true)
    setFeedback(null)

    const metadata = {}
    if (meta.newsflare_id) metadata.newsflare_id = meta.newsflare_id
    if (meta.title) metadata.title = meta.title
    if (meta.description) metadata.description = meta.description
    if (meta.uploader) metadata.uploader = meta.uploader
    if (meta.filming_location) metadata.filming_location = meta.filming_location
    if (meta.category) metadata.category = meta.category
    if (meta.is_exclusive) metadata.is_exclusive = true
    if (meta.tags) metadata.tags = meta.tags.split(',').map(t => t.trim()).filter(Boolean)

    try {
      const res = await ingest(file, metadata)
      setFeedback({
        type: 'success',
        message: `${res.message} (ID: ${res.video_id}, Status: ${res.status})`,
      })
      setFile(null)
      setMeta({ ...INITIAL_META })
    } catch (e) {
      setFeedback({ type: 'error', message: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>Ingest Video</h2>

      <div
        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <div className="icon">{file ? '\u2705' : '\u{1F4F9}'}</div>
        <p>{file ? '' : 'Drop a video here or click to select'}</p>
        {file && (
          <div className="file-name">
            {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
          </div>
        )}
      </div>

      <div className="section-title">Newsflare Metadata (optional)</div>

      <div className="metadata-form">
        <div className="form-group">
          <label>Newsflare ID</label>
          <input
            type="text"
            placeholder="NF-12345"
            value={meta.newsflare_id}
            onChange={(e) => updateMeta('newsflare_id', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Title</label>
          <input
            type="text"
            placeholder="Video title"
            value={meta.title}
            onChange={(e) => updateMeta('title', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Category</label>
          <input
            type="text"
            placeholder="e.g. News, Entertainment"
            value={meta.category}
            onChange={(e) => updateMeta('category', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Location</label>
          <input
            type="text"
            placeholder="Filming location"
            value={meta.filming_location}
            onChange={(e) => updateMeta('filming_location', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Uploader</label>
          <input
            type="text"
            placeholder="Uploader name/email"
            value={meta.uploader}
            onChange={(e) => updateMeta('uploader', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Tags (comma-separated)</label>
          <input
            type="text"
            placeholder="breaking, news, dramatic"
            value={meta.tags}
            onChange={(e) => updateMeta('tags', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            placeholder="Source description..."
            value={meta.description}
            onChange={(e) => updateMeta('description', e.target.value)}
          />
        </div>

        <div className="form-group checkbox-group">
          <input
            type="checkbox"
            id="exclusive"
            checked={meta.is_exclusive}
            onChange={(e) => updateMeta('is_exclusive', e.target.checked)}
          />
          <label htmlFor="exclusive">Exclusive Content</label>
        </div>
      </div>

      <button
        className="btn"
        onClick={handleIngest}
        disabled={!file || loading}
      >
        {loading ? 'Uploading...' : 'Ingest Video'}
      </button>

      {feedback && (
        <div className={`ingest-feedback ${feedback.type}`}>
          {feedback.message}
        </div>
      )}
    </div>
  )
}
