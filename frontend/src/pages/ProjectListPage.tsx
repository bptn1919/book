import { useEffect, useState } from 'react'
import { listProjects, logout, type ProjectSummary, type ProjectStatus } from '../api'
import { Nav } from '../components/Nav'

const STATUS_LABELS: Record<ProjectStatus, string> = {
  CREATED: 'Draft',
  STYLE_SET: 'In progress',
  CHARACTERS_GENERATED: 'In progress',
  PORTRAITS_GENERATED: 'In progress',
  CHAPTERS_GENERATED: 'In progress',
  DONE: 'Done',
}

const STATUS_ORDER: ProjectStatus[] = [
  'CREATED',
  'STYLE_SET',
  'CHARACTERS_GENERATED',
  'PORTRAITS_GENERATED',
  'CHAPTERS_GENERATED',
  'DONE',
]

function statusIndex(s: ProjectStatus) {
  return STATUS_ORDER.indexOf(s)
}

function pillClass(s: ProjectStatus) {
  if (s === 'DONE') return 'gd-pill ink'
  if (s === 'CREATED') return 'gd-pill gray'
  return 'gd-pill'
}

interface Props {
  user: { id: string; name: string }
  onNew: () => void
  onOpen: (id: string) => void
  onLogout: () => void
}

export function ProjectListPage({ user, onNew, onOpen, onLogout }: Props) {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null)

  useEffect(() => {
    listProjects().then(setProjects).catch(() => setProjects([]))
  }, [])

  async function handleLogout() {
    await logout().catch(() => {})
    onLogout()
  }

  return (
    <>
      <Nav user={user} onLogout={handleLogout} />
      <div className="app-body">
        <div className="list-head">
          <h2>My Projects</h2>
          <button className="gd-btn gd-btn-primary" onClick={onNew}>
            + New Project
          </button>
        </div>

        {projects === null && (
          <div style={{ textAlign: 'center', padding: '48px', color: 'var(--fg-3)' }}>
            <div className="spinner" style={{ margin: '0 auto' }} />
          </div>
        )}

        {projects !== null && projects.length === 0 && (
          <div className="empty-state">
            <p style={{ marginBottom: 0 }}>No projects yet.</p>
            <button className="gd-btn gd-btn-primary" onClick={onNew}>
              Create your first project
            </button>
          </div>
        )}

        {projects !== null && projects.length > 0 && (
          <div className="project-list">
            {projects.map((p, i) => (
              <div
                key={p.id}
                className="project-row"
                style={{ '--stagger': `${i * 40}ms` } as React.CSSProperties}
                onClick={() => onOpen(p.id)}
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && onOpen(p.id)}
                role="button"
              >
                <div className="title">
                  <h4>{p.title}</h4>
                  <div className="meta">
                    {new Date(p.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="progress-mini">
                  {STATUS_ORDER.slice(1).map((s, idx) => (
                    <span
                      key={s}
                      className={`seg${statusIndex(p.status) > idx ? ' on' : ''}`}
                    />
                  ))}
                </div>
                <span className={pillClass(p.status)}>
                  {p.status === 'CREATED' || p.status === 'DONE' ? null : (
                    <span className="dot" />
                  )}
                  {STATUS_LABELS[p.status]}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
