import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import Table from '../components/Table';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Pagination from '../components/Pagination';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreBadgeVariant(score) {
  if (score > 0.8) return 'success';
  if (score > 0.5) return 'warning';
  return 'default';
}

function cloudBadgeVariant(cloud) {
  const map = { AWS: 'warning', AZURE: 'info', GCP: 'success', ON_PREM: 'default' };
  return map[cloud] || 'default';
}

// ---------------------------------------------------------------------------
// Research Form
// ---------------------------------------------------------------------------

function ResearchForm({ onSuccess }) {
  const [form, setForm] = useState({ company_name: '', website: '', ticker: '' });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.company_name.trim()) return;
    setLoading(true);
    setMessage(null);
    try {
      const body = {
        company_name: form.company_name.trim(),
        ...(form.website.trim() && { website: form.website.trim() }),
        ...(form.ticker.trim() && { ticker: form.ticker.trim() }),
      };
      const res = await api.post('/api/v1/accounts/research', body);
      setMessage({
        type: 'success',
        text: `Successfully researched ${res.company_name}. Migration score: ${(res.migration_score * 100).toFixed(0)}%, ${res.signal_count} signal(s) found.`,
      });
      setForm({ company_name: '', website: '', ticker: '' });
      onSuccess?.();
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Research failed' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">Research Account</h2>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
              placeholder="e.g. Acme Corp"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
            <input
              type="text"
              value={form.website}
              onChange={(e) => setForm({ ...form, website: e.target.value })}
              placeholder="https://acme.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ticker</label>
            <input
              type="text"
              value={form.ticker}
              onChange={(e) => setForm({ ...form, ticker: e.target.value })}
              placeholder="ACME"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            />
          </div>
        </div>

        <div className="mt-4 flex items-center gap-4">
          <Button type="submit" loading={loading} disabled={!form.company_name.trim()}>
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Research Account
          </Button>

          {message && (
            <div
              className={`flex-1 text-sm px-4 py-2 rounded-lg ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-red-50 text-red-700 border border-red-200'
              }`}
            >
              {message.text}
            </div>
          )}
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Accounts Page
// ---------------------------------------------------------------------------

const PAGE_SIZE = 25;

export default function Accounts() {
  const navigate = useNavigate();

  const [targets, setTargets] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTargets = useCallback(async (currentOffset) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/api/v1/accounts/migration-targets', {
        offset: currentOffset,
        limit: PAGE_SIZE,
      });
      setTargets(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      setError(err.message || 'Failed to load migration targets');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTargets(offset);
  }, [offset, fetchTargets]);

  function handlePageChange(newOffset) {
    setOffset(newOffset);
  }

  function handleResearchSuccess() {
    setOffset(0);
    fetchTargets(0);
  }

  // -----------------------------------------------------------------------
  // Table columns
  // -----------------------------------------------------------------------

  const columns = [
    { key: 'company_name', label: 'Company Name' },
    { key: 'industry_name', label: 'Industry' },
    {
      key: 'migration_opportunity_score',
      label: 'Migration Score',
      render: (val) => {
        const pct = val != null ? (val * 100).toFixed(0) : 0;
        const variant = scoreBadgeVariant(val);
        const barColor =
          variant === 'success'
            ? 'bg-green-500'
            : variant === 'warning'
            ? 'bg-yellow-500'
            : 'bg-gray-400';
        return (
          <div className="flex items-center gap-2 min-w-[120px]">
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${barColor}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-600 w-9 text-right">{pct}%</span>
          </div>
        );
      },
    },
    {
      key: 'primary_cloud',
      label: 'Primary Cloud',
      render: (val) =>
        val ? <Badge variant={cloudBadgeVariant(val)}>{val}</Badge> : <span className="text-gray-400">--</span>,
    },
    {
      key: 'buying_signal_count',
      label: 'Signals',
      render: (val) => (
        <span className="text-sm text-gray-700 font-medium">{val ?? 0}</span>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <Button
          variant="secondary"
          className="text-xs px-2.5 py-1"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/accounts/${row.account_id}`);
          }}
        >
          View
        </Button>
      ),
    },
  ];

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Research Form */}
      <ResearchForm onSuccess={handleResearchSuccess} />

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Migration Targets Table */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">Migration Targets</h2>
          <span className="text-sm text-gray-500">{total} account{total !== 1 ? 's' : ''}</span>
        </div>
        <Table
          columns={columns}
          data={targets}
          loading={loading}
          emptyMessage="No migration targets found. Research an account above to get started."
          onRowClick={(row) => navigate(`/accounts/${row.account_id}`)}
        />
        <Pagination
          total={total}
          offset={offset}
          limit={PAGE_SIZE}
          onChange={handlePageChange}
        />
      </div>
    </div>
  );
}
