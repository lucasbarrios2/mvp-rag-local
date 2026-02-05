import { useState, useRef, useEffect, useMemo } from 'react'
import { ragQuery } from '../api'

function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // Headers: ### H3, ## H2, # H1
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h3>$1</h3>')
  // Bold: **text**
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // Italic: *text*
  html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
  // Bullet lists: lines starting with - or *
  html = html.replace(/^(?:[-*]) (.+)$/gm, '<li>$1</li>')
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
  // Numbered lists: lines starting with 1. 2. etc
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, (match) => {
    // Avoid double-wrapping already wrapped <ul>
    if (match.startsWith('<ul>')) return match
    return `<ul>${match}</ul>`
  })
  // Paragraphs: double newlines
  html = html.replace(/\n{2,}/g, '</p><p>')
  // Single newlines inside paragraphs → <br>
  html = html.replace(/\n/g, '<br>')
  // Wrap in <p> if not starting with a block element
  if (!html.startsWith('<h') && !html.startsWith('<ul')) {
    html = `<p>${html}</p>`
  }
  // Clean empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, '')
  return html
}

function FormattedContent({ text }) {
  const html = useMemo(() => renderMarkdown(text), [text])
  return <div className="formatted-content" dangerouslySetInnerHTML={{ __html: html }} />
}

export default function RAGChat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('text') // 'text' or 'video'
  const messagesEnd = useRef(null)

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(e) {
    e?.preventDefault()
    const q = input.trim()
    if (!q || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)

    try {
      const res = await ragQuery(q, {}, mode === 'video')
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          model: res.model_used,
        },
      ])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}`, error: true },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <h2>RAG Chat</h2>

      <div className="chat-toggle">
        <button
          className={mode === 'text' ? 'active' : ''}
          onClick={() => setMode('text')}
        >
          Text
        </button>
        <button
          className={mode === 'video' ? 'active' : ''}
          onClick={() => setMode('video')}
        >
          Video
        </button>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty">
            Ask questions about your video library. The RAG system will search relevant videos and generate answers.
            <br /><br />
            <strong>Text mode:</strong> Uses pre-analyzed text context (faster)
            <br />
            <strong>Video mode:</strong> Gemini watches the actual videos (slower, more accurate)
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            {msg.role === 'assistant' && !msg.error
              ? <FormattedContent text={msg.content} />
              : <div>{msg.content}</div>
            }
            {msg.sources?.length > 0 && (
              <div className="chat-sources">
                {msg.sources.map((s, j) => (
                  <span key={j} className="source-chip">
                    {s.filename || `Video #${s.video_id}`} ({s.score.toFixed(2)})
                  </span>
                ))}
              </div>
            )}
            {msg.model && (
              <div className="model-tag">Model: {msg.model}</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-message assistant">
            <span className="spinner" /> Thinking...
          </div>
        )}

        <div ref={messagesEnd} />
      </div>

      <form onSubmit={handleSend} className="chat-input">
        <input
          type="text"
          placeholder={mode === 'video'
            ? 'Ask a question (Gemini will watch videos)...'
            : 'Ask a question about your videos...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
