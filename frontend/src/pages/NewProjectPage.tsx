import { useRef, useState } from 'react'
import { createProject } from '../api'

interface Props {
  onBack: () => void
  onCreated: (id: string) => void
}

export function NewProjectPage({ onBack, onCreated }: Props) {
  const [title, setTitle] = useState('')
  const [bookFile, setBookFile] = useState<File | null>(null)
  const [bookText, setBookText] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function validate() {
    const e: Record<string, string> = {}
    if (!title.trim()) e.title = 'Title is required'
    if (!bookFile && !bookText.trim()) e.book = 'Upload a file or paste the book text'
    return e
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    setLoading(true)
    try {
      const result = await createProject(title.trim(), bookFile, bookText)
      onCreated(result.id)
    } catch {
      setErrors({ submit: 'Failed to create project. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file?.name.endsWith('.txt')) {
      setBookFile(file)
      setBookText('')
      setErrors(prev => ({ ...prev, book: '' }))
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null
    setBookFile(file)
    if (file) { setBookText(''); setErrors(prev => ({ ...prev, book: '' })) }
  }

  return (
    <div className="app-body narrow">
      <button className="back-link" onClick={onBack}>
        ← Back to projects
      </button>
      <h2>New Project</h2>
      <form onSubmit={handleSubmit}>
        <div className="gd-field">
          <label htmlFor="title">Title <span className="req">*</span></label>
          <input
            id="title"
            type="text"
            placeholder="e.g. The Wind in the Willows"
            value={title}
            onChange={e => { setTitle(e.target.value); setErrors(prev => ({ ...prev, title: '' })) }}
            disabled={loading}
            autoFocus
          />
          {errors.title && <div className="err">{errors.title}</div>}
        </div>

        <div style={{ marginTop: '20px' }}>
          <div
            className={`dropzone${bookFile ? ' has-file' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={handleDrop}
            tabIndex={0}
            role="button"
            aria-label="Upload book file"
            onKeyDown={e => e.key === 'Enter' && fileInputRef.current?.click()}
          >
            {bookFile
              ? <><strong>{bookFile.name}</strong><br /><span style={{ fontSize: 12, color: 'var(--fg-3)' }}>Click to change</span></>
              : <><div>Drop a <strong>.txt</strong> file here or click to browse</div><div className="hint">Plain text only · max 10 MB</div></>
            }
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,text/plain"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          <div className="divider-or">or</div>

          <div className="gd-field">
            <label htmlFor="book-text">Paste book text</label>
            <textarea
              id="book-text"
              rows={8}
              placeholder="Paste the full text of the book here…"
              value={bookText}
              onChange={e => {
                setBookText(e.target.value)
                if (e.target.value) setBookFile(null)
                setErrors(prev => ({ ...prev, book: '' }))
              }}
              disabled={loading || !!bookFile}
            />
          </div>
          {errors.book && <div className="err" style={{ marginTop: 6 }}>{errors.book}</div>}
        </div>

        {errors.submit && <div className="err" style={{ marginTop: 12 }}>{errors.submit}</div>}

        <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
          <button className="gd-btn gd-btn-primary" type="submit" disabled={loading}>
            {loading ? 'Creating…' : 'Create Project →'}
          </button>
          <button className="gd-btn gd-btn-secondary" type="button" onClick={onBack} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
