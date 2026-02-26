import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MarkdownRenderer from '../../components/MarkdownRenderer'

describe('MarkdownRenderer', () => {
  it('renders plain text content', () => {
    render(<MarkdownRenderer content="Hello world" />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
  })

  it('renders a level-1 markdown heading', () => {
    render(<MarkdownRenderer content="# Main Heading" />)
    expect(screen.getByRole('heading', { level: 1, name: 'Main Heading' })).toBeInTheDocument()
  })

  it('renders a level-2 markdown heading', () => {
    render(<MarkdownRenderer content="## Sub Heading" />)
    expect(screen.getByRole('heading', { level: 2, name: 'Sub Heading' })).toBeInTheDocument()
  })

  it('renders markdown list items', () => {
    render(<MarkdownRenderer content={'- item one\n- item two\n- item three'} />)
    expect(screen.getByText('item one')).toBeInTheDocument()
    expect(screen.getByText('item two')).toBeInTheDocument()
    expect(screen.getByText('item three')).toBeInTheDocument()
  })

  it('renders an ordered list', () => {
    render(<MarkdownRenderer content={'1. first\n2. second'} />)
    expect(screen.getByText('first')).toBeInTheDocument()
    expect(screen.getByText('second')).toBeInTheDocument()
  })

  it('renders markdown bold text inside a strong element', () => {
    render(<MarkdownRenderer content="**important**" />)
    const strong = document.querySelector('strong')
    expect(strong).toBeInTheDocument()
    expect(strong).toHaveTextContent('important')
  })

  it('renders markdown italic text inside an em element', () => {
    render(<MarkdownRenderer content="*emphasis*" />)
    const em = document.querySelector('em')
    expect(em).toBeInTheDocument()
    expect(em).toHaveTextContent('emphasis')
  })

  it('renders an inline code snippet', () => {
    render(<MarkdownRenderer content="`const x = 1`" />)
    const code = document.querySelector('code')
    expect(code).toBeInTheDocument()
    expect(code).toHaveTextContent('const x = 1')
  })

  it('renders empty content without crashing', () => {
    const { container } = render(<MarkdownRenderer content="" />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('wraps content in a prose container div', () => {
    const { container } = render(<MarkdownRenderer content="text" />)
    expect(container.firstChild).toHaveClass('prose')
  })
})
