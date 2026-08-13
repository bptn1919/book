interface Props {
  name: string
  prompt: string
  imageSrc: string | null
  aspectRatio: 'portrait' | 'chapter'
  stagger?: number
  generating?: boolean
}

export function EntityCard({ name, prompt, imageSrc, aspectRatio, stagger = 0, generating = false }: Props) {
  return (
    <div
      className="entity-card"
      style={{ '--stagger': `${stagger}ms` } as React.CSSProperties}
    >
      <div className={`art${aspectRatio === 'chapter' ? ' chapter' : ''}${!imageSrc ? ' pending' : ''}`}>
        {imageSrc ? (
          <img src={imageSrc} alt={name} loading="lazy" />
        ) : generating ? (
          <div style={{ textAlign: 'center' }}>
            <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
            <div className="placeholder-label" style={{ marginTop: 8 }}>Generating…</div>
          </div>
        ) : (
          <span className="placeholder-label muted">Pending</span>
        )}
      </div>
      <div className="body">
        <h5>{name}</h5>
        <p>{prompt.length > 120 ? prompt.slice(0, 120) + '…' : prompt}</p>
      </div>
    </div>
  )
}
