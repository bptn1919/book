import { useState } from 'react'
import type { Project } from '../api'

interface Props {
  project: Project
  stepError: string
  onRunStyle: (style: string) => void
  onRunCharacters: () => void
  onRunPortraits: () => void
  onRunChapters: () => void
  onRunIllustrations: () => void
}

const STEP_LABELS: Record<string, string> = {
  CREATED: 'Set art style',
  STYLE_SET: 'Generate characters',
  CHARACTERS_GENERATED: 'Generate portraits',
  PORTRAITS_GENERATED: 'Generate chapters',
  CHAPTERS_GENERATED: 'Generate illustrations',
}

const RUNNING_LABELS: Record<string, string> = {
  CREATED: 'Setting art style…',
  STYLE_SET: 'Generating characters…',
  CHARACTERS_GENERATED: 'Generating portraits…',
  PORTRAITS_GENERATED: 'Generating chapters…',
  CHAPTERS_GENERATED: 'Generating illustrations…',
}

export function StepPanel({
  project, stepError,
  onRunStyle, onRunCharacters, onRunPortraits, onRunChapters, onRunIllustrations,
}: Props) {
  const [styleInput, setStyleInput] = useState('')
  const running = project.step_state === 'RUNNING'
  const failed = project.step_state === 'FAILED'
  const status = project.status

  function handleAction() {
    switch (status) {
      case 'CREATED': return onRunStyle(styleInput)
      case 'STYLE_SET': return onRunCharacters()
      case 'CHARACTERS_GENERATED': return onRunPortraits()
      case 'PORTRAITS_GENERATED': return onRunChapters()
      case 'CHAPTERS_GENERATED': return onRunIllustrations()
    }
  }

  const btnLabel = failed
    ? `Retry: ${STEP_LABELS[status]}`
    : (STEP_LABELS[status] ?? '')

  return (
    <div className="step-panel">
      {running && (
        <div className="status-line">
          <div className="spinner" />
          {RUNNING_LABELS[status] ?? 'Working…'}
          <span style={{ fontSize: 11, color: 'var(--fg-3)', marginLeft: 4 }}>This may take 10–30s</span>
        </div>
      )}
      {failed && stepError && (
        <div className="status-line error">
          ⚠ {stepError}
        </div>
      )}
      {!running && failed && !stepError && (
        <div className="status-line error">
          ⚠ This step failed. You can retry it below.
        </div>
      )}

      {status === 'CREATED' && !running && (
        <div className="gd-field" style={{ marginBottom: 14 }}>
          <label htmlFor="style-input">Art style <span style={{ color: 'var(--fg-3)', fontWeight: 400 }}>(optional — leave blank for AI to choose)</span></label>
          <input
            id="style-input"
            type="text"
            placeholder="e.g. watercolor, soft pastels"
            value={styleInput}
            onChange={e => setStyleInput(e.target.value)}
            disabled={running}
          />
        </div>
      )}

      {!running && status !== 'DONE' && (
        <button className="gd-btn gd-btn-primary" onClick={handleAction}>
          {btnLabel}
        </button>
      )}

      {!running && status !== 'DONE' && (
        <p className="help" style={{ marginTop: 12 }}>
          {status === 'CREATED' && 'Gemini will read your book and set the style for all illustrations.'}
          {status === 'STYLE_SET' && 'Gemini will identify the main adult characters and describe them.'}
          {status === 'CHARACTERS_GENERATED' && 'Gemini will generate a portrait image for each character.'}
          {status === 'PORTRAITS_GENERATED' && 'Gemini will create a prompt for each chapter illustration.'}
          {status === 'CHAPTERS_GENERATED' && 'Gemini will illustrate each chapter, keeping characters consistent.'}
        </p>
      )}
    </div>
  )
}
