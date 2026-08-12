import { useState } from 'react'
import { login, register } from '../api'

interface Props {
  onAuth: (user: { id: string; name: string; email: string }) => void
}

export function IdentityPage({ onAuth }: Props) {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmedEmail = email.trim()
    const trimmedName = name.trim()
    if (!trimmedEmail) { setError('Email is required'); return }
    setLoading(true)
    setError('')
    try {
      // Try login first — if no account exists, register with name
      const user = await login(trimmedEmail).catch(async (err) => {
        if (err.status === 404) {
          if (!trimmedName) throw Object.assign(new Error('Name is required for new accounts'), { needsName: true })
          return register(trimmedName, trimmedEmail)
        }
        throw err
      })
      onAuth(user)
    } catch (err: unknown) {
      const e = err as { needsName?: boolean; message?: string }
      if (e.needsName) {
        setError('No account found. Enter your name to create one.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="center-page">
      <div className="auth-card">
        <div className="logo-row">Book Illustration Studio</div>
        <p className="lede">Enter your email to sign in or create an account. No password needed.</p>
        <form onSubmit={handleSubmit}>
          <div className="gd-field">
            <label htmlFor="email">Email <span className="req">*</span></label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => { setEmail(e.target.value); setError('') }}
              disabled={loading}
              autoFocus
            />
          </div>
          <div className="gd-field">
            <label htmlFor="name">Name <span className="req">*</span> <span style={{ fontWeight: 400, color: 'var(--fg-2)', fontSize: 12 }}>(required for new accounts)</span></label>
            <input
              id="name"
              type="text"
              placeholder="Your name"
              value={name}
              onChange={e => { setName(e.target.value); setError('') }}
              disabled={loading}
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
