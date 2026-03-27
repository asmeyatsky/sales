import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import Badge from '../components/Badge';
import Button from '../components/Button';
import Table from '../components/Table';
import Pagination from '../components/Pagination';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cloudBadgeVariant(cloud) {
  const map = { AWS: 'warning', AZURE: 'info', GCP: 'success', ON_PREM: 'default' };
  return map[cloud] || 'default';
}

function strengthVariant(strength) {
  const map = { CRITICAL: 'danger', STRONG: 'warning', MODERATE: 'warning', WEAK: 'default' };
  return map[strength] || 'default';
}

function signalTypeVariant(type) {
  const map = {
    NEW_EXECUTIVE: 'info',
    TECH_ADOPTION: 'success',
    BUDGET_SIGNAL: 'warning',
    PAIN_POINT: 'danger',
    EXPANSION: 'success',
    COMPETITIVE_THREAT: 'danger',
  };
  return map[type] || 'info';
}

function emailStatusVariant(status) {
  const map = { VALID: 'success', INVALID: 'danger', CATCH_ALL: 'warning', UNVALIDATED: 'default' };
  return map[status] || 'default';
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

// ---------------------------------------------------------------------------
// Score Display
// ---------------------------------------------------------------------------

function ScoreRing({ score }) {
  const pct = score != null ? Math.round(score * 100) : 0;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;
  const color =
    pct >= 80 ? 'text-green-500' : pct >= 50 ? 'text-yellow-500' : 'text-gray-400';

  return (
    <div className="relative inline-flex items-center justify-center w-20 h-20">
      <svg className="w-20 h-20 -rotate-90" viewBox="0 0 64 64">
        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          className="text-gray-200"
        />
        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={color}
        />
      </svg>
      <span className="absolute text-sm font-bold text-gray-900">{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Account Detail Page
// ---------------------------------------------------------------------------

const STAKEHOLDER_PAGE_SIZE = 15;

export default function AccountDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Account state
  const [account, setAccount] = useState(null);
  const [accountLoading, setAccountLoading] = useState(true);
  const [accountError, setAccountError] = useState(null);

  // Signals state
  const [signals, setSignals] = useState([]);
  const [signalsLoading, setSignalsLoading] = useState(true);

  // Stakeholders state
  const [stakeholders, setStakeholders] = useState([]);
  const [stakeholderTotal, setStakeholderTotal] = useState(0);
  const [stakeholderOffset, setStakeholderOffset] = useState(0);
  const [stakeholdersLoading, setStakeholdersLoading] = useState(true);

  // Action loading states
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [deckLoading, setDeckLoading] = useState(false);
  const [validatingId, setValidatingId] = useState(null);

  // Feedback messages
  const [actionMessage, setActionMessage] = useState(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchAccount = useCallback(async () => {
    setAccountLoading(true);
    setAccountError(null);
    try {
      const data = await api.get(`/api/v1/accounts/${id}`);
      setAccount(data);
    } catch (err) {
      setAccountError(err.message || 'Failed to load account');
    } finally {
      setAccountLoading(false);
    }
  }, [id]);

  const fetchSignals = useCallback(async () => {
    setSignalsLoading(true);
    try {
      const data = await api.get(`/api/v1/accounts/${id}/signals`);
      setSignals(Array.isArray(data) ? data : []);
    } catch {
      setSignals([]);
    } finally {
      setSignalsLoading(false);
    }
  }, [id]);

  const fetchStakeholders = useCallback(async (currentOffset) => {
    setStakeholdersLoading(true);
    try {
      const data = await api.get(`/api/v1/stakeholders/${id}`, {
        offset: currentOffset,
        limit: STAKEHOLDER_PAGE_SIZE,
      });
      setStakeholders(data.items || []);
      setStakeholderTotal(data.total || 0);
    } catch {
      setStakeholders([]);
      setStakeholderTotal(0);
    } finally {
      setStakeholdersLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAccount();
    fetchSignals();
  }, [fetchAccount, fetchSignals]);

  useEffect(() => {
    fetchStakeholders(stakeholderOffset);
  }, [stakeholderOffset, fetchStakeholders]);

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------

  async function handleDiscoverStakeholders() {
    if (!account) return;
    setDiscoverLoading(true);
    setActionMessage(null);
    try {
      const result = await api.post('/api/v1/stakeholders/discover', {
        account_id: account.account_id,
        company_name: account.company_name,
      });
      const count = Array.isArray(result) ? result.length : 0;
      setActionMessage({ type: 'success', text: `Discovered ${count} stakeholder(s).` });
      setStakeholderOffset(0);
      fetchStakeholders(0);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Discovery failed' });
    } finally {
      setDiscoverLoading(false);
    }
  }

  async function handleGenerateDeck() {
    if (!account) return;
    setDeckLoading(true);
    setActionMessage(null);
    try {
      await api.post('/api/v1/decks/generate', { account_id: account.account_id });
      setActionMessage({ type: 'success', text: 'Deck generation started successfully.' });
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Deck generation failed' });
    } finally {
      setDeckLoading(false);
    }
  }

  async function handleValidateStakeholder(stakeholderId) {
    setValidatingId(stakeholderId);
    try {
      await api.post(`/api/v1/stakeholders/${stakeholderId}/validate`);
      fetchStakeholders(stakeholderOffset);
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Validation failed' });
    } finally {
      setValidatingId(null);
    }
  }

  // -----------------------------------------------------------------------
  // Stakeholder table columns
  // -----------------------------------------------------------------------

  const stakeholderColumns = [
    { key: 'full_name', label: 'Name' },
    { key: 'job_title', label: 'Title' },
    {
      key: 'seniority',
      label: 'Seniority',
      render: (val) => <span className="text-sm capitalize">{val?.toLowerCase().replace(/_/g, ' ') || '--'}</span>,
    },
    {
      key: 'department',
      label: 'Department',
      render: (val) => <span className="text-sm capitalize">{val?.toLowerCase().replace(/_/g, ' ') || '--'}</span>,
    },
    {
      key: 'email_status',
      label: 'Email Status',
      render: (val) => <Badge variant={emailStatusVariant(val)}>{val || 'N/A'}</Badge>,
    },
    {
      key: 'relevance_score',
      label: 'Relevance',
      render: (val) => {
        if (val == null) return <span className="text-gray-400">--</span>;
        const pct = (val * 100).toFixed(0);
        return <span className="text-sm font-medium">{pct}%</span>;
      },
    },
    {
      key: 'persona_match_offering',
      label: 'Persona Match',
      render: (val, row) => {
        if (!val) return <span className="text-gray-400">--</span>;
        const conf = row.persona_match_confidence;
        return (
          <div className="text-sm">
            <span className="font-medium">{val}</span>
            {conf != null && (
              <span className="ml-1 text-gray-400">({(conf * 100).toFixed(0)}%)</span>
            )}
          </div>
        );
      },
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            className="text-xs px-2 py-1"
            loading={validatingId === row.stakeholder_id}
            onClick={(e) => {
              e.stopPropagation();
              handleValidateStakeholder(row.stakeholder_id);
            }}
          >
            Validate
          </Button>
          <Button
            variant="secondary"
            className="text-xs px-2 py-1"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/messages?account_id=${account?.account_id || ''}&stakeholder_id=${row.stakeholder_id}`);
            }}
          >
            Message
          </Button>
        </div>
      ),
    },
  ];

  // -----------------------------------------------------------------------
  // Loading / Error states
  // -----------------------------------------------------------------------

  if (accountLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-gray-200 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (accountError) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/accounts')}
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Accounts
        </button>
        <div className="rounded-lg bg-red-50 border border-red-200 px-6 py-8 text-center">
          <p className="text-red-700 font-medium">Failed to load account</p>
          <p className="mt-1 text-sm text-red-600">{accountError}</p>
          <Button className="mt-4" onClick={fetchAccount}>Retry</Button>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="space-y-8">
      {/* Back Link */}
      <button
        onClick={() => navigate('/accounts')}
        className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Accounts
      </button>

      {/* Account Header */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-gray-900">{account?.company_name}</h1>
            <div className="flex flex-wrap items-center gap-2">
              {account?.industry_name && (
                <Badge variant="info">{account.industry_name}</Badge>
              )}
              {account?.industry_vertical && (
                <span className="text-sm text-gray-500">{account.industry_vertical}</span>
              )}
              {account?.primary_cloud && (
                <Badge variant={cloudBadgeVariant(account.primary_cloud)}>
                  {account.primary_cloud}
                </Badge>
              )}
              {account?.company_size && (
                <Badge variant="default">{account.company_size}</Badge>
              )}
              {account?.is_high_intent && (
                <Badge variant="success">High Intent</Badge>
              )}
            </div>
            {account?.website && (
              <p className="text-sm text-gray-500">
                <a
                  href={account.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand hover:underline"
                >
                  {account.website}
                </a>
              </p>
            )}
            {account?.tech_stack_summary && (
              <p className="text-sm text-gray-500">
                <span className="font-medium text-gray-700">Tech Stack:</span> {account.tech_stack_summary}
              </p>
            )}
          </div>

          <div className="flex-shrink-0 flex flex-col items-center">
            <ScoreRing score={account?.migration_opportunity_score} />
            <span className="mt-1 text-xs font-medium text-gray-500 uppercase tracking-wide">
              Migration Score
            </span>
          </div>
        </div>
      </section>

      {/* Action Buttons */}
      <section>
        <div className="flex flex-wrap items-center gap-3">
          <Button loading={discoverLoading} onClick={handleDiscoverStakeholders}>
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Discover Stakeholders
          </Button>
          <Button variant="secondary" loading={deckLoading} onClick={handleGenerateDeck}>
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            Generate Deck
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate(`/messages?account_id=${account?.account_id || ''}`)}
          >
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Run Full Pipeline
          </Button>
        </div>

        {actionMessage && (
          <div
            className={`mt-3 text-sm px-4 py-2.5 rounded-lg ${
              actionMessage.type === 'success'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {actionMessage.text}
          </div>
        )}
      </section>

      {/* Buying Signals */}
      <section>
        <h2 className="text-base font-semibold text-gray-900 mb-4">
          Buying Signals
          {!signalsLoading && (
            <span className="ml-2 text-sm font-normal text-gray-500">({signals.length})</span>
          )}
        </h2>

        {signalsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : signals.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 px-6 py-10 text-center">
            <p className="text-sm text-gray-400">No buying signals detected for this account.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {signals.map((signal, idx) => (
              <div
                key={signal.signal_id || idx}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant={signalTypeVariant(signal.signal_type)}>
                    {signal.signal_type?.replace(/_/g, ' ') || 'SIGNAL'}
                  </Badge>
                  <Badge variant={strengthVariant(signal.strength)}>
                    {signal.strength || 'UNKNOWN'}
                  </Badge>
                  <span className="ml-auto text-xs text-gray-400">
                    {formatDate(signal.detected_at)}
                  </span>
                </div>
                <p className="text-sm text-gray-700 leading-relaxed">{signal.description}</p>
                {signal.source_url && (
                  <a
                    href={signal.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block text-xs text-brand hover:underline"
                  >
                    View source
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Stakeholders Table */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">
            Stakeholders
            {!stakeholdersLoading && (
              <span className="ml-2 text-sm font-normal text-gray-500">({stakeholderTotal})</span>
            )}
          </h2>
        </div>
        <Table
          columns={stakeholderColumns}
          data={stakeholders}
          loading={stakeholdersLoading}
          emptyMessage="No stakeholders found. Click 'Discover Stakeholders' to find contacts."
        />
        <Pagination
          total={stakeholderTotal}
          offset={stakeholderOffset}
          limit={STAKEHOLDER_PAGE_SIZE}
          onChange={setStakeholderOffset}
        />
      </section>
    </div>
  );
}
