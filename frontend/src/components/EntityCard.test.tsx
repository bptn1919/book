import { render, screen } from '@testing-library/react'
import { EntityCard } from './EntityCard'

describe('EntityCard', () => {
  it('renders the character name and prompt', () => {
    render(
      <EntityCard name="Mole" prompt="A small velvety creature." imageSrc={null} aspectRatio="portrait" />
    )
    expect(screen.getByText('Mole')).toBeInTheDocument()
    expect(screen.getByText('A small velvety creature.')).toBeInTheDocument()
  })

  it('shows Pending placeholder when no image', () => {
    render(
      <EntityCard name="Mole" prompt="desc" imageSrc={null} aspectRatio="portrait" />
    )
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('renders an image when imageSrc is provided', () => {
    render(
      <EntityCard name="Rat" prompt="desc" imageSrc="/api/projects/p1/images/portrait_0.png" aspectRatio="portrait" />
    )
    const img = screen.getByRole('img', { name: 'Rat' })
    expect(img).toHaveAttribute('src', '/api/projects/p1/images/portrait_0.png')
  })

  it('shows Generating spinner when generating=true and no image', () => {
    render(
      <EntityCard name="Mole" prompt="desc" imageSrc={null} aspectRatio="portrait" generating />
    )
    expect(screen.getByText('Generating…')).toBeInTheDocument()
    expect(screen.queryByText('Pending')).not.toBeInTheDocument()
  })

  it('truncates long prompts', () => {
    const long = 'a'.repeat(200)
    render(
      <EntityCard name="x" prompt={long} imageSrc={null} aspectRatio="portrait" />
    )
    expect(screen.getByText(/…$/)).toBeInTheDocument()
  })
})
