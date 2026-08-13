import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { IdentityPage } from './IdentityPage'
import * as api from '../api'

vi.mock('../api', () => ({
  login: vi.fn(),
  register: vi.fn(),
}))

const mockLogin = api.login as ReturnType<typeof vi.fn>
const mockRegister = api.register as ReturnType<typeof vi.fn>

describe('IdentityPage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders the name input and submit button', () => {
    render(<IdentityPage onAuth={() => {}} />)
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue/i })).toBeInTheDocument()
  })

  it('shows validation error when submitting empty name', async () => {
    render(<IdentityPage onAuth={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('calls login and fires onAuth on success', async () => {
    const user = { id: 'u1', name: 'Alice' }
    mockLogin.mockResolvedValue(user)
    const onAuth = vi.fn()
    render(<IdentityPage onAuth={onAuth} />)
    await userEvent.type(screen.getByLabelText(/name/i), 'Alice')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(onAuth).toHaveBeenCalledWith(user))
  })

  it('falls back to register when login returns 404', async () => {
    const err = Object.assign(new Error('Not found'), { status: 404 })
    mockLogin.mockRejectedValue(err)
    const user = { id: 'u2', name: 'Bob' }
    mockRegister.mockResolvedValue(user)
    const onAuth = vi.fn()
    render(<IdentityPage onAuth={onAuth} />)
    await userEvent.type(screen.getByLabelText(/name/i), 'Bob')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(onAuth).toHaveBeenCalledWith(user))
    expect(mockRegister).toHaveBeenCalledWith('Bob')
  })

  it('shows error message when both login and register fail', async () => {
    mockLogin.mockRejectedValue(new Error('Server error'))
    render(<IdentityPage onAuth={() => {}} />)
    await userEvent.type(screen.getByLabelText(/name/i), 'Alice')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(/something went wrong/i)).toBeInTheDocument())
  })
})
