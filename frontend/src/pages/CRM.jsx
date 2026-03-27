import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import Button from '../components/Button';
import Badge from '../components/Badge';
import Table from '../components/Table';
import Pagination from '../components/Pagination';
import Modal from '../components/Modal';

const RECORD_TYPES = ['LEAD', 'CONTACT', 'ACCOUNT', 'OPPORTUNITY', 'ACTIVITY'];
const PROVIDERS = ['salesforce', 'hubspot'];
const RESOLVE_STRATEGIES = [
  { value: 'LAST_WRITE_WINS', label: 'Last Write Wins' },
  { value: 'LOCAL_PRIORITY', label: 'Local Priority' },
  { value: 'REMOTE_PRIORITY', label: 'Remote Priority' },
  { value: 'MANUAL_FLAG', label: 'Manual Flag' },
];

const PROVIDER_BADGE = {
  salesforce: 'info',
  hubspot: 'warning',
};

const CONFLICT_STATUS_BADGE = {
  PENDING: 'warning',
  RESOLVED: 'success',
  FLAGGED: 'info',
  pending: 'warning',
  resolved: 'success',
  flagged: 'info',
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

// --- Push to CRM form ---
function PushForm() {
  const [localId, setLocalId] = useState('');
  const [recordType, setRecordType] = useState('LEAD');
  const [provider, setProvider] = useState('salesforce');
  const [fields, setFields] = useState('{}');
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState(null);
  const [pushError, setPushError] = useState(null);

  async function handlePush(e) {
    e.preventDefault();
    setPushing(true);
    setPushError(null);
    setPushResult(null);
    try {
      let parsedFields;
      try {
        parsedFields = JSON.parse(fields);
      } catch {
        throw new Error('Invalid JSON in fields');
      }
      const res = await api.post('/api/v1/crm/push', {
        local_id: localId.trim(),
        record_type: recordType,
        provider,
        fields: parsedFields,
      });
      setPushResult(res);
    } catch (err) {
      setPushError(err.message);
    } finally {
      setPushing(false);
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex-1">
      <h4 className="text-base font-semibold text-gray-900 mb-4">Push to CRM</h4>
      <form onSubmit={handlePush} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Local ID</label>
          <input
            type="text"
            value={localId}
            onChange={(e) => setLocalId(e.target.value)}
            placeholder="Enter local record ID"
            required
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Record Type</label>
            <select
              value={recordType}
              onChange={(e) => setRecordType(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            >
              {RECORD_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fields (JSON)</label>
          <textarea
            value={fields}
            onChange={(e) => setFields(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-none"
          />
        </div>
        <Button type="submit" loading={pushing}>Push</Button>
      </form>

      {pushError && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2">
          <p className="text-sm text-red-700">{pushError}</p>
        </div>
      )}
      {pushResult && (
        <div className="mt-3 rounded-lg border border-green-200 bg-green-50 px-4 py-2">
          <p className="text-sm text-green-700">Successfully pushed record to CRM.</p>
        </div>
      )}
    </div>
  );
}

// --- Pull from CRM form ---
function PullForm() {
  const [provider, setProvider] = useState('salesforce');
  const [recordType, setRecordType] = useState('LEAD');
  const [since, setSince] = useState('');
  const [pulling, setPulling] = useState(false);
  const [pullResult, setPullResult] = useState(null);
  const [pullError, setPullError] = useState(null);

  async function handlePull(e) {
    e.preventDefault();
    setPulling(true);
    setPullError(null);
    setPullResult(null);
    try {
      const body = { provider, record_type: recordType };
      if (since) body.since = since;
      const res = await api.post('/api/v1/crm/pull', body);
      setPullResult(res);
    } catch (err) {
      setPullError(err.message);
    } finally {
      setPulling(false);
    }
  }

  const resultCount =
    pullResult?.count ??
    pullResult?.total ??
    pullResult?.records?.length ??
    pullResult?.items?.length ??
    null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex-1">
      <h4 className="text-base font-semibold text-gray-900 mb-4">Pull from CRM</h4>
      <form onSubmit={handlePull} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            >
              {PROVIDERS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Record Type</label>
            <select
              value={recordType}
              onChange={(e) => setRecordType(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            >
              {RECORD_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Since</label>
          <input
            type="datetime-local"
            value={since}
            onChange={(e) => setSince(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
          />
        </div>
        <Button type="submit" loading={pulling}>Pull</Button>
      </form>

      {pullError && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2">
          <p className="text-sm text-red-700">{pullError}</p>
        </div>
      )}
      {pullResult && (
        <div className="mt-3 rounded-lg border border-green-200 bg-green-50 px-4 py-2">
          <p className="text-sm text-green-700">
            Pull complete.
            {resultCount !== null && (
              <span className="font-medium"> {resultCount} record{resultCount !== 1 ? 's' : ''} synced.</span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

// --- Main CRM page ---
export default function CRM() {
  // Conflicts state
  const [conflicts, setConflicts] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const limit = 25;

  // Resolve modal state
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [resolveTarget, setResolveTarget] = useState(null);
  const [resolveStrategy, setResolveStrategy] = useState('LAST_WRITE_WINS');
  const [resolving, setResolving] = useState(false);
  const [resolveError, setResolveError] = useState(null);

  const fetchConflicts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPaginated('/api/v1/crm/conflicts', offset, limit);
      setConflicts(res.items || res.data || res.conflicts || []);
      setTotal(res.total ?? res.count ?? 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    fetchConflicts();
  }, [fetchConflicts]);

  function openResolveModal(conflict) {
    setResolveTarget(conflict);
    setResolveStrategy('LAST_WRITE_WINS');
    setResolveError(null);
    setShowResolveModal(true);
  }

  async function handleResolve() {
    if (!resolveTarget) return;
    setResolving(true);
    setResolveError(null);
    try {
      await api.post(`/api/v1/crm/conflicts/${resolveTarget.id}/resolve`, {
        strategy: resolveStrategy,
      });
      setShowResolveModal(false);
      setResolveTarget(null);
      await fetchConflicts();
    } catch (err) {
      setResolveError(err.message);
    } finally {
      setResolving(false);
    }
  }

  const conflictColumns = [
    {
      key: 'record_id',
      label: 'Record ID',
      render: (val, row) => (
        <span className="font-mono text-xs text-gray-600">{truncate(row.record_id || row.id)}</span>
      ),
    },
    {
      key: 'provider',
      label: 'Provider',
      render: (val, row) => (
        <Badge variant={PROVIDER_BADGE[row.provider] || 'default'}>
          {row.provider}
        </Badge>
      ),
    },
    {
      key: 'record_type',
      label: 'Record Type',
      render: (val, row) => (
        <span className="text-sm text-gray-700">{row.record_type}</span>
      ),
    },
    {
      key: 'local_id',
      label: 'Local ID',
      render: (val, row) => (
        <span className="font-mono text-xs text-gray-500">{truncate(row.local_id)}</span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (val, row) => (
        <Badge variant={CONFLICT_STATUS_BADGE[row.status] || 'default'}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: 'last_synced',
      label: 'Last Synced',
      render: (val, row) => (
        <span className="text-xs text-gray-500">{formatDate(row.last_synced_at || row.last_synced)}</span>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (val, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            openResolveModal(row);
          }}
          className="text-brand hover:text-brand-dark text-sm font-medium transition-colors"
        >
          Resolve
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      {/* Sync Actions */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Sync Actions</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PushForm />
          <PullForm />
        </div>
      </div>

      {/* Sync Conflicts */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Sync Conflicts</h3>
          {!loading && (
            <span className="text-sm text-gray-500">{total} conflict{total !== 1 ? 's' : ''}</span>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm text-red-700">Failed to load conflicts: {error}</p>
            <button
              onClick={fetchConflicts}
              className="mt-1 text-sm font-medium text-red-800 underline hover:no-underline"
            >
              Retry
            </button>
          </div>
        )}

        <Table
          columns={conflictColumns}
          data={conflicts}
          loading={loading}
          emptyMessage="No sync conflicts found."
        />
        <Pagination
          total={total}
          offset={offset}
          limit={limit}
          onChange={setOffset}
        />
      </div>

      {/* Resolve Modal */}
      <Modal
        isOpen={showResolveModal}
        onClose={() => {
          setShowResolveModal(false);
          setResolveTarget(null);
          setResolveError(null);
        }}
        title="Resolve Conflict"
      >
        <div className="space-y-4">
          {resolveTarget && (
            <div className="text-sm text-gray-600">
              <p>
                Resolving conflict for record{' '}
                <span className="font-mono font-medium text-gray-800">
                  {truncate(resolveTarget.record_id || resolveTarget.id, 24)}
                </span>
              </p>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Resolution Strategy
            </label>
            <select
              value={resolveStrategy}
              onChange={(e) => setResolveStrategy(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            >
              {RESOLVE_STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          {resolveError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2">
              <p className="text-sm text-red-700">{resolveError}</p>
            </div>
          )}
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                setShowResolveModal(false);
                setResolveTarget(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleResolve} loading={resolving}>
              Resolve
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
