import { render, screen } from '@testing-library/react'
import { Stepper } from './Stepper'

describe('Stepper', () => {
  it('marks step 1 as current when status is CREATED', () => {
    render(<Stepper status="CREATED" stepState="IDLE" />)
    const step1 = screen.getByText('1')
    expect(step1.closest('.step')).toHaveClass('current')
  })

  it('marks completed steps as done', () => {
    render(<Stepper status="CHARACTERS_GENERATED" stepState="IDLE" />)
    // Steps 1 and 2 are done (Style, Characters)
    expect(screen.getByText('1').closest('.gd-num-square')).toHaveClass('done')
    expect(screen.getByText('2').closest('.gd-num-square')).toHaveClass('done')
  })

  it('marks future steps as pending', () => {
    render(<Stepper status="CREATED" stepState="IDLE" />)
    expect(screen.getByText('2').closest('.step')).toHaveClass('pending')
    expect(screen.getByText('5').closest('.step')).toHaveClass('pending')
  })

  it('renders all 5 step labels', () => {
    render(<Stepper status="DONE" stepState="IDLE" />)
    expect(screen.getByText('Style')).toBeInTheDocument()
    expect(screen.getByText('Characters')).toBeInTheDocument()
    expect(screen.getByText('Portraits')).toBeInTheDocument()
    expect(screen.getByText('Chapters')).toBeInTheDocument()
    expect(screen.getByText('Illustrations')).toBeInTheDocument()
  })
})
