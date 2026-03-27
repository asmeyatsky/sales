const STEP_LABELS = ['LI Request', 'Email 1', 'LI Message', 'Email 2', 'Phone'];

function StepDot({ status }) {
  if (status === 'completed') {
    return (
      <div className="w-9 h-9 rounded-full bg-green-500 flex items-center justify-center shadow-sm">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }

  if (status === 'current') {
    return (
      <div className="relative w-9 h-9 flex items-center justify-center">
        <span className="absolute inline-flex h-full w-full rounded-full bg-brand opacity-30 animate-ping" />
        <span className="relative inline-flex w-9 h-9 rounded-full bg-brand shadow-sm" />
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="w-9 h-9 rounded-full bg-red-500 flex items-center justify-center shadow-sm">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    );
  }

  // pending
  return (
    <div className="w-9 h-9 rounded-full bg-gray-300 shadow-sm" />
  );
}

function getStepStatus(step, index, currentStepIndex) {
  if (!step) return 'pending';
  if (step.executed_at && step.success === false) return 'failed';
  if (index === currentStepIndex) return 'current';
  if (step.executed_at && step.success !== false) return 'completed';
  return 'pending';
}

function getLineColor(status) {
  if (status === 'completed') return 'bg-green-500';
  if (status === 'failed') return 'bg-red-500';
  return 'bg-gray-300';
}

export default function SequenceTimeline({ steps = [], currentStepIndex = 0 }) {
  // Build a 5-step array, filling gaps with null
  const allSteps = Array.from({ length: 5 }, (_, i) => {
    return steps.find((s) => s.step_number === i + 1) || null;
  });

  return (
    <div className="flex items-start justify-between w-full max-w-2xl mx-auto py-4">
      {allSteps.map((step, i) => {
        const status = getStepStatus(step, i, currentStepIndex);
        const label = STEP_LABELS[i] || `Step ${i + 1}`;

        return (
          <div key={i} className="flex items-start flex-1 last:flex-none">
            {/* Step column */}
            <div className="flex flex-col items-center">
              <StepDot status={status} />
              <span className="mt-2 text-xs font-medium text-gray-600 text-center leading-tight whitespace-nowrap">
                {label}
              </span>
              {step?.scheduled_at && (
                <span className="mt-0.5 text-[10px] text-gray-400">
                  {new Date(step.scheduled_at).toLocaleDateString()}
                </span>
              )}
            </div>

            {/* Connector line */}
            {i < 4 && (
              <div className="flex-1 flex items-center pt-4 px-1">
                <div
                  className={`h-0.5 w-full rounded-full ${getLineColor(status)}`}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
