import type { ProjectStatus, StepState } from '../api'

const STEPS: { label: string }[] = [
  { label: 'Style' },
  { label: 'Characters' },
  { label: 'Portraits' },
  { label: 'Chapters' },
  { label: 'Illustrations' },
]

const STATUS_ORDER: ProjectStatus[] = [
  'CREATED',
  'STYLE_SET',
  'CHARACTERS_GENERATED',
  'PORTRAITS_GENERATED',
  'CHAPTERS_GENERATED',
  'DONE',
]

function idx(s: ProjectStatus) { return STATUS_ORDER.indexOf(s) }

interface Props {
  status: ProjectStatus
  stepState: StepState
}

export function Stepper({ status, stepState: _stepState }: Props) {
  const currentIdx = idx(status)

  return (
    <div className="stepper" aria-label="Pipeline steps">
      {STEPS.map((step, i) => {
        const stepIdx = i + 1   // step number (1-based)
        const isDone = currentIdx >= stepIdx
        const isCurrent = currentIdx === stepIdx - 1
        const isPending = !isDone && !isCurrent

        let squareCls = 'gd-num-square'
        if (isDone) squareCls += ' done'
        else if (isPending) squareCls += ' gray'

        let stepCls = 'step'
        if (isCurrent) stepCls += ' current'
        else if (isPending) stepCls += ' pending'

        return (
          <div key={step.label} style={{ display: 'contents' }}>
            {i > 0 && (
              <div className={`connector${currentIdx >= stepIdx ? ' done' : ''}`} />
            )}
            <div className={stepCls}>
              <div className={squareCls}>{i + 1}</div>
              <span className="lbl">{step.label}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
