const BASE = '/api/v1'

const API_KEY = localStorage.getItem('rag_api_key') || ''

function headers(extra = {}) {
  const h = { ...extra }
  const key = localStorage.getItem('rag_api_key') || ''
  if (key) h['X-API-Key'] = key
  return h
}

function jsonHeaders() {
  return headers({ 'Content-Type': 'application/json' })
}

async function request(url, options = {}) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export async function health() {
  return request('/health')
}

export async function stats() {
  return request(`${BASE}/stats`, { headers: headers() })
}

export async function search(query, filters = {}, limit = 10) {
  return request(`${BASE}/search`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ query, filters, limit }),
  })
}

export async function similar(videoId, limit = 5) {
  return request(`${BASE}/search/similar/${videoId}`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ limit }),
  })
}

export async function ragQuery(query, filters = {}, includeVideo = false, limit = 5) {
  return request(`${BASE}/rag/query`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      query,
      filters,
      limit,
      include_video_analysis: includeVideo,
      max_videos_for_analysis: 3,
    }),
  })
}

export async function videoContext(videoId) {
  return request(`${BASE}/videos/${videoId}/context`, {
    headers: headers(),
  })
}

export async function ingest(file, metadata = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('metadata', JSON.stringify(metadata))
  return request(`${BASE}/videos/ingest`, {
    method: 'POST',
    headers: headers(),
    body: formData,
  })
}

export async function updateMetadata(videoId, metadata) {
  return request(`${BASE}/videos/${videoId}/metadata`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(metadata),
  })
}

export async function deleteVideo(videoId) {
  return request(`${BASE}/videos/${videoId}`, {
    method: 'DELETE',
    headers: headers(),
  })
}

export async function listVideos(status = '') {
  const url = status
    ? `${BASE}/videos?status=${encodeURIComponent(status)}`
    : `${BASE}/videos`
  return request(url, { headers: headers() })
}
