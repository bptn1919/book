import { useEffect, useState } from 'react'
import { getMe } from './api'
import { IdentityPage } from './pages/IdentityPage'
import { ProjectListPage } from './pages/ProjectListPage'
import { NewProjectPage } from './pages/NewProjectPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'

export type Route =
  | { page: 'identity' }
  | { page: 'list' }
  | { page: 'new' }
  | { page: 'detail'; id: string }

interface User { id: string; name: string; email: string }

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [route, setRoute] = useState<Route>({ page: 'list' })

  useEffect(() => {
    getMe()
      .then(u => setUser(u))
      .catch(() => setUser(null))
  }, [])

  if (user === undefined) return null

  if (!user) {
    return (
      <IdentityPage
        onAuth={u => {
          setUser(u)
          setRoute({ page: 'list' })
        }}
      />
    )
  }

  return (
    <>
      {route.page === 'list' && (
        <ProjectListPage
          user={user}
          onNew={() => setRoute({ page: 'new' })}
          onOpen={id => setRoute({ page: 'detail', id })}
          onLogout={() => setUser(null)}
        />
      )}
      {route.page === 'new' && (
        <NewProjectPage
          onBack={() => setRoute({ page: 'list' })}
          onCreated={id => setRoute({ page: 'detail', id })}
        />
      )}
      {route.page === 'detail' && (
        <ProjectDetailPage
          projectId={route.id}
          user={user}
          onBack={() => setRoute({ page: 'list' })}
          onLogout={() => setUser(null)}
        />
      )}
    </>
  )
}
