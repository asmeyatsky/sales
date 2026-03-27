import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Table from '../components/Table';
import Modal from '../components/Modal';
import SequenceTimeline from '../components/SequenceTimeline';

const STATUS_BADGE = {
  ACTIVE: 'success',
  PAUSED: 'warning',
  STOPPED: 'danger',
  COMPLETED: 'info',
  DRAFT: 'default',
};

const STEP_STATUS_BADGE = {
  success: 'success',
  fail: 'danger',
  failed: 'danger',
  pending: 'default',
  scheduled: 'info',
  executed: 'success',
};

const STEP_TYPE_BADGE = {
  email: 'info',
  linkedin: 'info',
  linkedin_request: 'info',
  linkedin_message: 'info',
  call: 'success',
  phone: 'success',
  sms: 'warning',
  wait: 'default',
};

function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function truncate(str, len = 16) {
  if (!str) return '-';
  return str.length > len ? str.slice(0, len) + '...' : str;
}

export default function SequenceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [sequence, setSequence] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [showStopModal, setShowStopModal] = useState(false);
  const [stopReason, setStopReason] = useState('');
  const [actionError, setActionError] = useState(null);

  const fetchSequence = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/api/v1/sequences/${id}`);
      setSequence(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSequence();
  }, [fetchSequence]);

  async function handleExecuteStep() {
    setExecuting(true);
    setActionError(null);
    try {
      await api.post(`/api/v1/sequences/${id}/execute-step`);
      await fetchSequence();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setExecuting(false);
    }
  }

  async function handleStop() {
    setStopping(true);
    setActionError(null);
    try {
      await api.post(`/api/v1/sequences/${id}/stop`, { reason: stopReason });
      setShowStopModal(false);
      setStopReason('');
      await fetchSequence();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setStopping(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-gray-200 rounded animate-pulse" />
        <div className="h-40 bg-gray-200 rounded-xl animate-pulse" />
        <div className="h-64 bg-gray-200 rounded-xl animate-pulse" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-8 text-center">
        <p className="text-sm text-red-700">Failed to load sequence: {error}</p>
        <div className="mt-4 flex justify-center gap-3">
          <Button variant="secondary" onClick={() => navigate('/sequences')}>
            Back to Sequences
          </Button>
          <Button onClick={fetchSequence}>Retry</Button>
        </div>
      </div>
    );
  }

  if (!sequence) return null;

  const steps = sequence.steps || [];
  const currentStepIndex = sequence.current_step_index ?? 0;
  const status = sequence.status || 'DRAFT';

  const stepColumns = [
    {
      key: 'step_number',
      label: 'Step #',
      render: (val, row) => (
        <span className="font-mono text-sm font-medium text-gray-800">
          {row.step_number ?? (steps.indexOf(row) + 1)}
        </span>
      ),
    },
    {
      key: 'step_type',
      label: 'Type',
      render: (val, row) => (
        <Badge variant={STEP_TYPE_BADGE[row.step_type] || 'default'}>
          {row.step_type || 'unknown'}
        </Badge>
      ),
    },
    {
      key: 'message_id',
      label: 'Message ID',
      render: (val, row) => (
        <span className="font-mono text-xs text-gray-500">
          {truncate(row.message_id)}
        </span>
      ),
    },
    {
      key: 'scheduled_at',
      label: 'Scheduled At',
      render: (val, row) => (
        <span className="text-xs text-gray-500">{formatDate(row.scheduled_at)}</span>
      ),
    },
    {
      key: 'executed_at',
      label: 'Executed At',
      render: (val, row) => (
        <span className="text-xs text-gray-500">{formatDate(row.executed_at)}</span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (val, row) => {
        let stepStatus = 'pending';
        if (row.executed_at && row.success === false) stepStatus = 'fail';
        else if (row.executed_at) stepStatus = 'success';
        else if (row.scheduled_at) stepStatus = 'scheduled';
        return (
          <Badge variant={STEP_STATUS_BADGE[stepStatus] || 'default'}>
            {stepStatus}
          </Badge>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Back nav */}
      <button
        onClick={() => navigate('/sequences')}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Sequences
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-gray-900">Sequence</h2>
            <Badge variant={STATUS_BADGE[status] || 'default'}>{status}</Badge>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500">
            <span>
              <span className="font-medium text-gray-600">ID:</span>{' '}
              <span className="font-mono">{truncate(sequence.id, 24)}</span>
            </span>
            <span>
              <span className="font-medium text-gray-600">Account:</span>{' '}
              {truncate(sequence.account_id, 20)}
            </span>
            <span>
              <span className="font-medium text-gray-600">Stakeholder:</span>{' '}
              {truncate(sequence.stakeholder_id, 20)}
            </span>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">
          Sequence Timeline
        </h3>
        <SequenceTimeline steps={steps} currentStepIndex={currentStepIndex} />
      </div>

      {/* Steps detail table */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
          Steps Detail
        </h3>
        <Table
          columns={stepColumns}
          data={steps}
          emptyMessage="No steps defined for this sequence."
        />
      </div>

      {/* Action error */}
      {actionError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">{actionError}</p>
        </div>
      )}

      {/* Actions bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
          Actions
        </h3>

        {status === 'ACTIVE' && (
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleExecuteStep} loading={executing}>
              Execute Next Step
            </Button>
            <Button variant="danger" onClick={() => setShowStopModal(true)}>
              Stop Sequence
            </Button>
          </div>
        )}

        {status === 'PAUSED' && (
          <div className="flex items-center gap-3 rounded-lg bg-yellow-50 border border-yellow-200 px-4 py-3">
            <svg className="w-5 h-5 text-yellow-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <p className="text-sm text-yellow-800">
              This sequence is paused. Manual intervention may be required to resume.
            </p>
          </div>
        )}

        {status === 'STOPPED' && (
          <div className="flex items-center gap-3 rounded-lg bg-red-50 border border-red-200 px-4 py-3">
            <svg className="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            <div>
              <p className="text-sm font-medium text-red-800">Sequence stopped</p>
              {sequence.stop_reason && (
                <p className="text-sm text-red-700 mt-0.5">Reason: {sequence.stop_reason}</p>
              )}
            </div>
          </div>
        )}

        {status === 'COMPLETED' && (
          <div className="flex items-center gap-3 rounded-lg bg-blue-50 border border-blue-200 px-4 py-3">
            <svg className="w-5 h-5 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-blue-800">
              This sequence has been completed successfully.
            </p>
          </div>
        )}
      </div>

      {/* Stop modal */}
      <Modal
        isOpen={showStopModal}
        onClose={() => {
          setShowStopModal(false);
          setStopReason('');
        }}
        title="Stop Sequence"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Are you sure you want to stop this sequence? This action cannot be undone.
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason for stopping
            </label>
            <textarea
              value={stopReason}
              onChange={(e) => setStopReason(e.target.value)}
              placeholder="Enter the reason for stopping this sequence..."
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-none"
            />
          </div>
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setShowStopModal(false);
                setStopReason('');
              }}
            >
              Cancel
            </Button>
            <Button variant="danger" onClick={handleStop} loading={stopping}>
              Stop Sequence
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
