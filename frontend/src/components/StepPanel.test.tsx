import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { StepPanel } from './StepPanel'

describe('StepPanel', () => {
  const project = {
    id: 'p1',
    title: 'Book',
    status: 'CHARACTERS_GENERATED',
    step_state: 'FAILED',
    step_started_at: null,
    art_style: null,
    created_at: '2026-08-12T00:00:00.000Z',
    is_stuck: false,
    characters: [],
    chapters: [],
  } as const

  it('shows the retry hint immediately when the step failed', () => {
    render(
      <StepPanel
        project={project}
        stepError="Something went wrong. Please try again."
        onRunStyle={vi.fn()}
        onRunCharacters={vi.fn()}
        onRunPortraits={vi.fn()}
        onRunChapters={vi.fn()}
        onRunIllustrations={vi.fn()}
      />,
    )

    expect(screen.getByText(/this step failed/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry: generate portraits/i })).toBeInTheDocument()
  })

  it('invokes retry in one click when the failed retry button is pressed', async () => {
    const onRunPortraits = vi.fn()

    render(
      <StepPanel
        project={project}
        stepError="Something went wrong. Please try again."
        onRunStyle={vi.fn()}
        onRunCharacters={vi.fn()}
        onRunPortraits={onRunPortraits}
        onRunChapters={vi.fn()}
        onRunIllustrations={vi.fn()}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /retry: generate portraits/i }))
    expect(onRunPortraits).toHaveBeenCalledTimes(1)
  })
})