import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import Table from '../components/Table';
import Pagination from '../components/Pagination';
import Badge from '../components/Badge';

const STATUS_BADGE = {
  ACTIVE: 'success',
  PAUSED: 'warning',
  STOPPED: 'danger',
  COMPLETED: 'info',
  DRAFT: 'default',
};

function ProgressBar({ current, total, status }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  const barColor = {
    ACTIVE: 'bg-green-500',
    PAUSED: 'bg-yellow-500',
    STOPPED: 'bg-red-500',
    COMPLETED: 'bg-blue-500',
    DRAFT: 'bg-gray-400',
  }[status] || 'bg-gray-400';

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 tabular-nums">{pct}%</span>
    </div>
  );
}

function truncate(str, len = 12) {
  if (!str) return '-';
  return str.length > len ? str.slice(0, len) + '...' : str;
}

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

export default function Sequences() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const limit = 25;

  const fetchSequences = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPaginated('/api/v1/sequences/active', offset, limit);
      setData(res.items || res.data || res.sequences || []);
      setTotal(res.total ?? res.count ?? 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    fetchSequences();
  }, [fetchSequences]);

  const columns = [
    {
      key: 'id',
      label: 'Sequence ID',
      render: (val, row) => (
        <span className="font-mono text-xs text-gray-600">{truncate(row.id)}</span>
      ),
    },
    {
      key: 'account_id',
      label: 'Account',
      render: (val, row) => (
        <span className="font-medium text-gray-800">{truncate(row.account_id, 16)}</span>
      ),
    },
    {
      key: 'stakeholder_id',
      label: 'Stakeholder',
      render: (val, row) => truncate(row.stakeholder_id, 16) || '-',
    },
    {
      key: 'status',
      label: 'Status',
      render: (val, row) => (
        <Badge variant={STATUS_BADGE[row.status] || 'default'}>{row.status}</Badge>
      ),
    },
    {
      key: 'current_step',
      label: 'Current Step',
      render: (val, row) => {
        const current = (row.current_step_index ?? 0) + 1;
        const total = row.total_steps ?? row.steps?.length ?? 5;
        return (
          <span className="text-sm font-medium text-gray-700">
            {current}/{total}
          </span>
        );
      },
    },
    {
      key: 'progress',
      label: 'Progress',
      render: (val, row) => {
        const current = (row.current_step_index ?? 0) + 1;
        const total = row.total_steps ?? row.steps?.length ?? 5;
        return <ProgressBar current={current} total={total} status={row.status} />;
      },
    },
    {
      key: 'started_at',
      label: 'Started At',
      render: (val, row) => (
        <span className="text-xs text-gray-500">{formatDate(row.started_at || row.created_at)}</span>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (val, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/sequences/${row.id}`);
          }}
          className="text-brand hover:text-brand-dark text-sm font-medium transition-colors"
        >
          View
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Active Sequences</h2>
          {!loading && (
            <p className="mt-1 text-sm text-gray-500">
              {total} active sequence{total !== 1 ? 's' : ''}
            </p>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            Failed to load sequences: {error}
          </p>
          <button
            onClick={fetchSequences}
            className="mt-1 text-sm font-medium text-red-800 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Sequences table */}
      <Table
        columns={columns}
        data={data}
        loading={loading}
        emptyMessage="No active sequences found."
        onRowClick={(row) => navigate(`/sequences/${row.id}`)}
      />

      {/* Pagination */}
      <Pagination
        total={total}
        offset={offset}
        limit={limit}
        onChange={setOffset}
      />
    </div>
  );
}
