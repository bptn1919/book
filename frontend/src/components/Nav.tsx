interface Props {
  user: { id: string; name: string; email: string }
  onLogout: () => void
}

export function Nav({ user, onLogout }: Props) {
  const initial = user.name[0]?.toUpperCase() ?? '?'
  return (
    <nav className="gd-nav">
      <div className="gd-nav-inner">
        <span className="gd-nav-logo">Book Illustration Studio</span>
        <div className="gd-nav-user">
          <div className="gd-nav-avatar" aria-hidden>{initial}</div>
          <span>{user.name}</span>
          <button onClick={onLogout}>Sign out</button>
        </div>
      </div>
    </nav>
  )
}
