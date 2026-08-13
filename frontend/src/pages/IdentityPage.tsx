import { useState } from 'react'
import { login, register } from '../api'

interface Props {
  onAuth: (user: { id: string; name: string }) => void
}

export function IdentityPage({ onAuth }: Props) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) { setError('Name is required'); return }
    setLoading(true)
    setError('')
    try {
      const user = await login(trimmed).catch(async (err) => {
        if (err.status === 404) return register(trimmed)
        throw err
      })
      onAuth(user)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="center-page">
      <div className="auth-card">
        <div className="logo-row">Book Illustration Studio</div>
        <p className="lede">Enter your name to continue. No password needed.</p>
        <form onSubmit={handleSubmit}>
          <div className="gd-field">
            <label htmlFor="name">Name <span className="req">*</span></label>
            <input
              id="name"
              type="text"
              placeholder="Your name"
              value={name}
              onChange={e => { setName(e.target.value); setError('') }}
              disabled={loading}
              autoFocus
            />
            {error && <div className="err">{error}</div>}
          </div>
          <button className="gd-btn gd-btn-primary" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Continue →'}
          </button>
        </form>
      </div>
    </div>
  )
}
