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

  it('renders email and name inputs with a submit button', () => {
    render(<IdentityPage onAuth={() => {}} />)
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue/i })).toBeInTheDocument()
  })

  it('shows validation error when submitting empty email', async () => {
    render(<IdentityPage onAuth={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('calls login with email and fires onAuth on success', async () => {
    const user = { id: 'u1', name: 'Alice', email: 'alice@example.com' }
    mockLogin.mockResolvedValue(user)
    const onAuth = vi.fn()
    render(<IdentityPage onAuth={onAuth} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(onAuth).toHaveBeenCalledWith(user))
    expect(mockLogin).toHaveBeenCalledWith('alice@example.com')
  })

  it('prompts to enter name when login returns 404 and name is empty', async () => {
    const err = Object.assign(new Error('Not found'), { status: 404 })
    mockLogin.mockRejectedValue(err)
    render(<IdentityPage onAuth={() => {}} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'new@example.com')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(/no account found/i)).toBeInTheDocument())
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('calls register with name and email when login returns 404 and name is provided', async () => {
    const err = Object.assign(new Error('Not found'), { status: 404 })
    mockLogin.mockRejectedValue(err)
    const user = { id: 'u2', name: 'Bob', email: 'bob@example.com' }
    mockRegister.mockResolvedValue(user)
    const onAuth = vi.fn()
    render(<IdentityPage onAuth={onAuth} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'bob@example.com')
    await userEvent.type(screen.getByLabelText(/name/i), 'Bob')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(onAuth).toHaveBeenCalledWith(user))
    expect(mockRegister).toHaveBeenCalledWith('Bob', 'bob@example.com')
  })

  it('shows generic error when login fails with a non-404 error', async () => {
    mockLogin.mockRejectedValue(new Error('Server error'))
    render(<IdentityPage onAuth={() => {}} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com')
    await userEvent.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByText(/something went wrong/i)).toBeInTheDocument())
  })
})
