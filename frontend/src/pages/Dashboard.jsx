import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import Card from '../components/Card';
import Table from '../components/Table';
import Button from '../components/Button';
import Modal from '../components/Modal';
import Badge from '../components/Badge';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatUptime(seconds) {
  if (seconds == null) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function cloudBadgeVariant(cloud) {
  const map = { AWS: 'warning', AZURE: 'info', GCP: 'success', ON_PREM: 'default' };
  return map[cloud] || 'default';
}

function scoreBadgeVariant(score) {
  if (score > 0.8) return 'success';
  if (score > 0.5) return 'warning';
  return 'default';
}

// ---------------------------------------------------------------------------
// Research Modal
// ---------------------------------------------------------------------------

function ResearchModal({ isOpen, onClose }) {
  const [form, setForm] = useState({ company_name: '', website: '', ticker: '' });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  function reset() {
    setForm({ company_name: '', website: '', ticker: '' });
    setResult(null);
    setError(null);
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.company_name.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        company_name: form.company_name.trim(),
        ...(form.website.trim() && { website: form.website.trim() }),
        ...(form.ticker.trim() && { ticker: form.ticker.trim() }),
      };
      const res = await api.post('/api/v1/accounts/research', body);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Research failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Research Account">
      {result ? (
        <div className="space-y-4">
          <div className="rounded-lg bg-green-50 border border-green-200 p-4">
            <p className="text-sm font-medium text-green-800">Research complete</p>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Company</span>
                <p className="font-medium text-gray-900">{result.company_name}</p>
              </div>
              <div>
                <span className="text-gray-500">Migration Score</span>
                <p className="font-medium text-gray-900">{(result.migration_score * 100).toFixed(0)}%</p>
              </div>
              <div>
                <span className="text-gray-500">Signals Found</span>
                <p className="font-medium text-gray-900">{result.signal_count}</p>
              </div>
              <div>
                <span className="text-gray-500">Account ID</span>
                <p className="font-medium text-gray-900 truncate">{result.account_id}</p>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={handleClose}>Close</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
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
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={handleClose}>Cancel</Button>
            <Button type="submit" loading={loading} disabled={!form.company_name.trim()}>
              Research
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Dashboard Page
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const navigate = useNavigate();

  // Stats state
  const [uptime, setUptime] = useState(null);
  const [migrationCount, setMigrationCount] = useState(null);
  const [sequenceCount, setSequenceCount] = useState(null);
  const [conflictCount, setConflictCount] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Recent targets state
  const [recentTargets, setRecentTargets] = useState([]);
  const [targetsLoading, setTargetsLoading] = useState(true);

  // Modal
  const [researchOpen, setResearchOpen] = useState(false);

  // Error
  const [error, setError] = useState(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const [metrics, migrations, sequences, conflicts] = await Promise.allSettled([
        api.get('/api/v1/metrics'),
        api.get('/api/v1/accounts/migration-targets', { limit: 1 }),
        api.get('/api/v1/sequences/active', { limit: 1 }),
        api.get('/api/v1/crm/conflicts', { limit: 1 }),
      ]);

      if (metrics.status === 'fulfilled') setUptime(metrics.value.uptime_seconds);
      if (migrations.status === 'fulfilled') setMigrationCount(migrations.value.total);
      if (sequences.status === 'fulfilled') setSequenceCount(sequences.value.total);
      if (conflicts.status === 'fulfilled') setConflictCount(conflicts.value.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const fetchRecentTargets = useCallback(async () => {
    setTargetsLoading(true);
    try {
      const res = await api.get('/api/v1/accounts/migration-targets', { limit: 5 });
      setRecentTargets(res.items || []);
    } catch {
      // silently fail -- stats area will show the issue
    } finally {
      setTargetsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchRecentTargets();
  }, [fetchStats, fetchRecentTargets]);

  // -----------------------------------------------------------------------
  // Table columns
  // -----------------------------------------------------------------------

  const columns = [
    { key: 'company_name', label: 'Company' },
    {
      key: 'migration_opportunity_score',
      label: 'Score',
      render: (val) => (
        <Badge variant={scoreBadgeVariant(val)}>
          {val != null ? `${(val * 100).toFixed(0)}%` : '--'}
        </Badge>
      ),
    },
    { key: 'industry_name', label: 'Industry' },
    {
      key: 'primary_cloud',
      label: 'Primary Cloud',
      render: (val) =>
        val ? <Badge variant={cloudBadgeVariant(val)}>{val}</Badge> : <span className="text-gray-400">--</span>,
    },
  ];

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-8">
      {/* Error banner */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Stats Cards */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card
            title="System Status"
            value={statsLoading ? '...' : uptime != null ? formatUptime(uptime) : 'N/A'}
            subtitle="Uptime"
            accent="border-t-green-500"
          />
          <Card
            title="Migration Targets"
            value={statsLoading ? '...' : migrationCount ?? 0}
            subtitle="Accounts above threshold"
            accent="border-t-brand"
          />
          <Card
            title="Active Sequences"
            value={statsLoading ? '...' : sequenceCount ?? 0}
            subtitle="Running outreach"
            accent="border-t-yellow-500"
          />
          <Card
            title="CRM Conflicts"
            value={statsLoading ? '...' : conflictCount ?? 0}
            subtitle="Pending resolution"
            accent="border-t-red-500"
          />
        </div>
      </section>

      {/* Quick Actions */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => setResearchOpen(true)}>
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Research Account
          </Button>
          <Button variant="secondary" onClick={() => navigate('/accounts')}>
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
            View Migration Targets
          </Button>
        </div>
      </section>

      {/* Recent High-Intent Accounts */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Recent High-Intent Accounts
        </h2>
        <Table
          columns={columns}
          data={recentTargets}
          loading={targetsLoading}
          emptyMessage="No high-intent accounts found yet. Research an account to get started."
          onRowClick={(row) => navigate(`/accounts/${row.account_id}`)}
        />
      </section>

      {/* Research Modal */}
      <ResearchModal isOpen={researchOpen} onClose={() => setResearchOpen(false)} />
    </div>
  );
}
