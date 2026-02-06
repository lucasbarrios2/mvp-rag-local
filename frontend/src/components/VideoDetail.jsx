import { useState } from 'react'
import { similar, updateMetadata, deleteVideo } from '../api'

export default function VideoDetail({ video, onFindSimilar, onDeleted }) {
  const [tab, setTab] = useState('info')
  const [metaForm, setMetaForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  if (!video) return null

  const tabs = [
    { id: 'info', label: 'Info' },
    { id: 'visual', label: 'Visual' },
    { id: 'narrative', label: 'Narrative' },
    { id: 'metadata', label: 'Metadata' },
  ]

  function startEdit() {
    setMetaForm({
      category: video.category || '',
      filming_location: video.filming_location || '',
      uploader: video.uploader || '',
      newsflare_id: video.newsflare_id || '',
      is_exclusive: video.is_exclusive || false,
      tags: (video.source_tags || []).join(', '),
    })
    setSaveMsg(null)
  }

  async function handleSave() {
    setSaving(true)
    setSaveMsg(null)
    try {
      const data = { ...metaForm }
      if (data.tags) {
        data.tags = data.tags.split(',').map(t => t.trim()).filter(Boolean)
      } else {
        delete data.tags
      }
      const res = await updateMetadata(video.id, data)
      setSaveMsg({ type: 'success', text: res.message })
      setMetaForm(null)
    } catch (e) {
      setSaveMsg({ type: 'error', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="detail-panel">
      <h3>{video.filename}</h3>
      <span className={`status-badge ${video.processing_status}`}>
        {video.processing_status}
      </span>

      <div className="detail-tabs" style={{ marginTop: 16 }}>
        {tabs.map(t => (
          <button
            key={t.id}
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'info' && (
        <div>
          <Field label="Filename" value={video.filename} />
          <Field label="File Size" value={video.file_size_bytes ? `${(video.file_size_bytes / 1024 / 1024).toFixed(1)} MB` : '-'} />
          <Field label="Duration" value={video.duration_seconds ? `${video.duration_seconds.toFixed(1)}s` : '-'} />
          <Field label="MIME Type" value={video.mime_type} mono />
          <Field label="Created" value={video.created_at ? new Date(video.created_at).toLocaleString() : '-'} />
          <Field label="Analyzed" value={video.analyzed_at ? new Date(video.analyzed_at).toLocaleString() : '-'} />
          <Field label="Embedding ID" value={video.unified_embedding_id} mono />
        </div>
      )}

      {tab === 'visual' && (
        <div>
          <Field label="Description" value={video.visual_description} />
          {video.visual_tags?.length > 0 && (
            <div className="detail-field">
              <div className="field-label">Tags</div>
              <div className="tags-list">
                {video.visual_tags.map((t, i) => <span key={i} className="tag">{t}</span>)}
              </div>
            </div>
          )}
          {video.objects_detected?.length > 0 && (
            <div className="detail-field">
              <div className="field-label">Objects Detected</div>
              <div className="tags-list">
                {video.objects_detected.map((o, i) => <span key={i} className="tag">{o}</span>)}
              </div>
            </div>
          )}
          <Field label="Visual Style" value={video.visual_style} />
        </div>
      )}

      {tab === 'narrative' && (
        <div>
          <Field label="Description" value={video.narrative_description} />
          <Field label="Emotional Tone" value={video.emotional_tone} />
          <Field label="Intensity" value={video.intensity != null ? `${video.intensity} / 10` : '-'} />
          <Field label="Viral Potential" value={video.viral_potential != null ? `${video.viral_potential} / 10` : '-'} />
          <Field label="Target Audience" value={video.target_audience} />

          {video.narrative_tags?.length > 0 && (
            <div className="detail-field">
              <div className="field-label">Tags</div>
              <div className="tags-list">
                {video.narrative_tags.map((t, i) => <span key={i} className="tag">{t}</span>)}
              </div>
            </div>
          )}

          {video.themes && Object.keys(video.themes).length > 0 && (
            <div className="detail-field">
              <div className="field-label">Themes</div>
              <div className="themes-grid">
                {Object.entries(video.themes).map(([name, score]) => (
                  <div key={name} className="theme-row">
                    <span className="theme-name">{name}</span>
                    <div className="theme-bar">
                      <div className="theme-fill" style={{ width: `${(Number(score) * 100).toFixed(0)}%` }} />
                    </div>
                    <span className="theme-score">{typeof score === 'number' ? score.toFixed(2) : score}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {video.key_moments?.length > 0 && (
            <div className="detail-field">
              <div className="field-label">Key Moments</div>
              <div className="key-moments-list">
                {video.key_moments.map((m, i) => (
                  <div key={i} className="moment-item">
                    <span className="moment-time">{formatTimestamp(m)}</span>
                    <span className="moment-desc">{m.event || m.description || JSON.stringify(m)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'metadata' && (
        <div>
          <Field label="Source" value={video.source} />
          <Field label="Newsflare ID" value={video.newsflare_id} mono />
          <Field label="Category" value={video.category} />
          <Field label="Location" value={video.filming_location} />
          <Field label="Uploader" value={video.uploader} />
          <Field label="Exclusive" value={video.is_exclusive ? 'Yes' : 'No'} />
          <Field label="Source Description" value={video.source_description} />
          {video.source_tags?.length > 0 && (
            <div className="detail-field">
              <div className="field-label">Source Tags</div>
              <div className="tags-list">
                {video.source_tags.map((t, i) => <span key={i} className="tag">{t}</span>)}
              </div>
            </div>
          )}

          {metaForm ? (
            <div style={{ marginTop: 16 }}>
              <div className="section-title">Edit Metadata</div>
              <div className="metadata-form">
                <div className="form-group">
                  <label>Category</label>
                  <input value={metaForm.category} onChange={e => setMetaForm(prev => ({ ...prev, category: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Location</label>
                  <input value={metaForm.filming_location} onChange={e => setMetaForm(prev => ({ ...prev, filming_location: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Uploader</label>
                  <input value={metaForm.uploader} onChange={e => setMetaForm(prev => ({ ...prev, uploader: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Newsflare ID</label>
                  <input value={metaForm.newsflare_id} onChange={e => setMetaForm(prev => ({ ...prev, newsflare_id: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Tags (comma-separated)</label>
                  <input value={metaForm.tags} onChange={e => setMetaForm(prev => ({ ...prev, tags: e.target.value }))} />
                </div>
                <div className="form-group checkbox-group">
                  <input type="checkbox" checked={metaForm.is_exclusive} onChange={e => setMetaForm(prev => ({ ...prev, is_exclusive: e.target.checked }))} />
                  <label>Exclusive</label>
                </div>
              </div>
              <div className="detail-actions">
                <button className="btn btn-sm" onClick={handleSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button className="btn btn-sm btn-outline" onClick={() => setMetaForm(null)}>Cancel</button>
              </div>
            </div>
          ) : null}

          {saveMsg && (
            <div className={`ingest-feedback ${saveMsg.type}`} style={{ marginTop: 12 }}>
              {saveMsg.text}
            </div>
          )}
        </div>
      )}

      <div className="detail-actions" style={{ marginTop: 20 }}>
        <button className="btn btn-sm btn-outline" onClick={onFindSimilar}>
          Find Similar
        </button>
        {tab === 'metadata' && !metaForm && (
          <button className="btn btn-sm btn-outline" onClick={startEdit}>
            Update Metadata
          </button>
        )}
        {!confirmDelete ? (
          <button
            className="btn btn-sm btn-danger"
            onClick={() => setConfirmDelete(true)}
          >
            Delete
          </button>
        ) : (
          <>
            <button
              className="btn btn-sm btn-danger"
              disabled={deleting}
              onClick={async () => {
                setDeleting(true)
                try {
                  await deleteVideo(video.id)
                  onDeleted?.(video.id)
                } catch (e) {
                  setSaveMsg({ type: 'error', text: e.message })
                  setConfirmDelete(false)
                } finally {
                  setDeleting(false)
                }
              }}
            >
              {deleting ? 'Deleting...' : 'Confirm Delete'}
            </button>
            <button
              className="btn btn-sm btn-outline"
              onClick={() => setConfirmDelete(false)}
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function formatTimestamp(m) {
  let secs = null
  if (m.timestamp_ms != null) secs = m.timestamp_ms / 1000
  else if (m.timestamp != null) secs = Number(m.timestamp)
  else if (m.time != null) secs = Number(m.time)
  if (secs == null || isNaN(secs)) return '?:??'
  const mins = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function Field({ label, value, mono }) {
  return (
    <div className="detail-field">
      <div className="field-label">{label}</div>
      <div className={`field-value ${mono ? 'mono' : ''}`}>{value || '-'}</div>
    </div>
  )
}
