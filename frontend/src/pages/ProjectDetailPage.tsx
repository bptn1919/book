import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getProject, runStyle, runCharacters, runPortraits, runChapters,
  runIllustrations, logout, imageUrl, type Project,
} from '../api'
import { Nav } from '../components/Nav'
import { Stepper } from '../components/Stepper'
import { StepPanel } from '../components/StepPanel'
import { EntityCard } from '../components/EntityCard'

const POLL_INTERVAL = 3000

interface Props {
  projectId: string
  user: { id: string; name: string; email: string }
  onBack: () => void
  onLogout: () => void
}


export function ProjectDetailPage({ projectId, user, onBack, onLogout }: Props) {
  const [project, setProject] = useState<Project | null>(null)
  const [loadErr, setLoadErr] = useState(false)
  const [stepErr, setStepErr] = useState('')
  const [bookOpen, setBookOpen] = useState(false)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback(async () => {
    try {
      const p = await getProject(projectId)
      setProject(p)
      return p
    } catch {
      setLoadErr(true)
      return null
    }
  }, [projectId])

  useEffect(() => {
    load()
  }, [load])

  // Poll while step is RUNNING
  useEffect(() => {
    if (!project) return
    if (project.step_state === 'RUNNING') {
      pollRef.current = setTimeout(async () => {
        await load()
      }, POLL_INTERVAL)
    }
    return () => { if (pollRef.current) clearTimeout(pollRef.current) }
  }, [project, load])

  async function runStep(fn: () => Promise<unknown>) {
    setStepErr('')
    try {
      await fn()
    } catch (err: unknown) {
      const e = err as { status?: number; message?: string }
      if (e.status !== 409) {
        setStepErr(e.message ?? 'Something went wrong. Please try again.')
      }
      // 409 = already running — fall through to load() so polling starts
    }
    await load()  // always reload; useEffect picks up RUNNING and starts polling
  }

  async function handleLogout() {
    await logout().catch(() => {})
    onLogout()
  }

  if (loadErr) {
    return (
      <>
        <Nav user={user} onLogout={handleLogout} />
        <div className="app-body narrow">
          <button className="back-link" onClick={onBack}>← Back</button>
          <p style={{ color: 'var(--grad-orange-deep)' }}>Failed to load project.</p>
        </div>
      </>
    )
  }

  if (!project) {
    return (
      <>
        <Nav user={user} onLogout={handleLogout} />
        <div className="app-body" style={{ textAlign: 'center', paddingTop: 80 }}>
          <div className="spinner" style={{ margin: '0 auto' }} />
        </div>
      </>
    )
  }

  const running = project.step_state === 'RUNNING'
  const failed = project.step_state === 'FAILED'
  const done = project.status === 'DONE'

  return (
    <>
      <Nav user={user} onLogout={handleLogout} />
      <div className="app-body">
        <button className="back-link" onClick={onBack}>← All projects</button>
        <h2 style={{ marginBottom: 4 }}>{project.title}</h2>
        <div className="meta" style={{ marginBottom: 32 }}>
          Created {new Date(project.created_at).toLocaleDateString()}
          {' · '}
          <button
            className="gd-btn-ghost"
            style={{ fontSize: 12, color: 'var(--grad-orange)' }}
            onClick={() => setBookOpen(true)}
          >
            View book text
          </button>
        </div>

        <Stepper status={project.status} stepState={project.step_state} />

        <div className="detail-grid">
          {/* Left: content panels */}
          <div>
            {/* Characters */}
            {project.characters.length > 0 && (
              <section style={{ marginBottom: 32 }}>
                <div className="panel-title"><h3>Characters</h3></div>
                <div className="entity-grid">
                  {project.characters.map((c, i) => (
                    <EntityCard
                      key={c.id}
                      name={c.name}
                      prompt={c.prompt}
                      imageSrc={c.portrait_path ? imageUrl(projectId, c.portrait_path) : null}
                      aspectRatio="portrait"
                      stagger={i * 60}
                      generating={running && project.status === 'CHARACTERS_GENERATED' && !c.portrait_path}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Chapters */}
            {project.chapters.length > 0 && (
              <section style={{ marginBottom: 32 }}>
                <div className="panel-title"><h3>Chapters</h3></div>
                <div className="entity-grid">
                  {project.chapters.map((ch, i) => (
                    <EntityCard
                      key={ch.id}
                      name={ch.name}
                      prompt={ch.prompt}
                      imageSrc={ch.illustration_path ? imageUrl(projectId, ch.illustration_path) : null}
                      aspectRatio="chapter"
                      stagger={i * 60}
                      generating={running && project.status === 'CHAPTERS_GENERATED' && !ch.illustration_path}
                    />
                  ))}
                </div>
              </section>
            )}

            {done && (
              <div style={{ padding: '24px', background: 'var(--grad-paper)', borderRadius: 12, textAlign: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>🎉</div>
                <h3 style={{ marginBottom: 4 }}>All done!</h3>
                <p style={{ color: 'var(--fg-2)', margin: 0 }}>Your book has been fully illustrated.</p>
              </div>
            )}
          </div>

          {/* Right: step panel + style */}
          <div>
            {!done && (
              <StepPanel
                project={project}
                stepError={stepErr}
                onRunStyle={style => runStep(() => runStyle(projectId, style))}
                onRunCharacters={() => runStep(() => runCharacters(projectId))}
                onRunPortraits={() => runStep(() => runPortraits(projectId))}
                onRunChapters={() => runStep(() => runChapters(projectId))}
                onRunIllustrations={() => runStep(() => runIllustrations(projectId))}
              />
            )}

            {project.art_style && (
              <div className="side-note" style={{ marginTop: done ? 0 : 16 }}>
                <h5>Art style</h5>
                <p>{project.art_style}</p>
              </div>
            )}

            {(running || failed) && project.is_stuck && (
              <div style={{ marginTop: 12, padding: 12, background: '#fff7f3', borderRadius: 8, border: '1px solid var(--grad-orange-pale)', fontSize: 13, color: 'var(--grad-orange-deep)' }}>
                This step appears stuck. Clicking the action button above will override it.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Book text modal */}
      {bookOpen && (
        <BookModal projectId={projectId} onClose={() => setBookOpen(false)} />
      )}
    </>
  )
}

function BookModal({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const [text, setText] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/projects/${projectId}/book`, { credentials: 'include' })
      .then(r => r.ok ? r.text() : Promise.reject())
      .then(setText)
      .catch(() => setText('(Could not load book text.)'))
  }, [projectId])

  return (
    <div
      className="modal-overlay"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="modal-box" role="dialog" aria-modal aria-labelledby="book-modal-title">
        <div className="modal-head">
          <h4 id="book-modal-title" style={{ margin: 0 }}>Full book text</h4>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">
          {text === null ? <div className="spinner" /> : text}
        </div>
      </div>
    </div>
  )
}
