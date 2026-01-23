import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { I18nextProvider } from 'react-i18next'
import YouTubeImportForm from '../YouTubeImportForm'
import { ToastProvider } from '../../../hooks/useToast'
import i18n from '../../../i18n'

// Mock i18n
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue: string) => defaultValue || key,
  }),
  I18nextProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <ToastProvider>
      {component}
    </ToastProvider>
  )
}

describe('YouTubeImportForm', () => {
  it('renders without crashing', () => {
    renderWithProviders(<YouTubeImportForm />)
    expect(screen.getByText(/Импорт из YouTube/i)).toBeInTheDocument()
  })

  it('renders URL input field', () => {
    renderWithProviders(<YouTubeImportForm />)
    const input = screen.getByPlaceholderText(/youtube\.com/i)
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'url')
  })

  it('renders import type buttons', () => {
    renderWithProviders(<YouTubeImportForm />)
    expect(screen.getByText(/Playlist/i)).toBeInTheDocument()
    expect(screen.getByText(/Video/i)).toBeInTheDocument()
  })

  it('renders quality options', () => {
    renderWithProviders(<YouTubeImportForm />)
    expect(screen.getByText('Auto')).toBeInTheDocument()
    expect(screen.getByText('1080p')).toBeInTheDocument()
    expect(screen.getByText('720p')).toBeInTheDocument()
    expect(screen.getByText('480p')).toBeInTheDocument()
    expect(screen.getByText('Audio Only')).toBeInTheDocument()
  })

  it('renders import button', () => {
    renderWithProviders(<YouTubeImportForm />)
    const button = screen.getByRole('button', { name: /Импортировать/i })
    expect(button).toBeInTheDocument()
  })

  it('disables button when URL is empty', () => {
    renderWithProviders(<YouTubeImportForm />)
    const button = screen.getByRole('button', { name: /Импортировать/i })
    expect(button).toBeDisabled()
  })

  it('enables button when URL is entered', () => {
    renderWithProviders(<YouTubeImportForm />)
    const input = screen.getByPlaceholderText(/youtube\.com/i)
    const button = screen.getByRole('button', { name: /Импортировать/i })

    fireEvent.change(input, { target: { value: 'https://youtube.com/watch?v=test' } })

    expect(button).not.toBeDisabled()
  })

  it('switches between import types', () => {
    renderWithProviders(<YouTubeImportForm />)
    const playlistButton = screen.getByText('Playlist')
    const videoButton = screen.getByText('Video')

    // Initially playlist should be selected
    expect(playlistButton.parentElement).toHaveClass('bg-red-500')

    // Click video button
    fireEvent.click(videoButton)

    // Video should now be selected
    expect(videoButton.parentElement).toHaveClass('bg-red-500')
    expect(playlistButton.parentElement).not.toHaveClass('bg-red-500')
  })

  it('switches between quality options', () => {
    renderWithProviders(<YouTubeImportForm />)
    const autoButton = screen.getByText('Auto')
    const p1080Button = screen.getByText('1080p')

    // Initially auto should be selected
    expect(autoButton.parentElement).toHaveClass('bg-red-500')

    // Click 1080p button
    fireEvent.click(p1080Button)

    // 1080p should now be selected
    expect(p1080Button.parentElement).toHaveClass('bg-red-500')
    expect(autoButton.parentElement).not.toHaveClass('bg-red-500')
  })

  it('shows loading state when submitting', async () => {
    renderWithProviders(<YouTubeImportForm />)
    const input = screen.getByPlaceholderText(/youtube\.com/i)
    const button = screen.getByRole('button', { name: /Импортировать/i })

    fireEvent.change(input, { target: { value: 'https://youtube.com/watch?v=test' } })
    fireEvent.click(button)

    // Button should show loading state
    await waitFor(() => {
      expect(button).toBeDisabled()
    })
  })
})
