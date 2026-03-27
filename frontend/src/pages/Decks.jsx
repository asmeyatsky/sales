import { useState, useCallback } from 'react';
import { api } from '../api';
import Button from '../components/Button';
import Table from '../components/Table';
import Pagination from '../components/Pagination';

const OFFERINGS = [
  { value: '', label: 'Auto-detect' },
  { value: 'Cloud Migration', label: 'Cloud Migration' },
  { value: 'Applied AI / GenAI', label: 'Applied AI / GenAI' },
  { value: 'Data & Analytics', label: 'Data & Analytics' },
  { value: 'Future of Work', label: 'Future of Work' },
];

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

export default function Decks() {
  // --- Generate Deck form state ---
  const [genAccountId, setGenAccountId] = useState('');
  const [offering, setOffering] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState(null);
  const [generatedDeck, setGeneratedDeck] = useState(null);

  // --- Account decks lookup state ---
  const [lookupAccountId, setLookupAccountId] = useState('');
  const [decks, setDecks] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [lookupError, setLookupError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const limit = 25;

  async function handleGenerate(e) {
    e.preventDefault();
    if (!genAccountId.trim()) return;
    setGenerating(true);
    setGenError(null);
    setGeneratedDeck(null);
    try {
      const body = { account_id: genAccountId.trim() };
      if (offering) body.offering = offering;
      const res = await api.post('/api/v1/decks/generate', body);
      setGeneratedDeck(res);
    } catch (err) {
      setGenError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  const fetchDecks = useCallback(
    async (newOffset) => {
      if (!lookupAccountId.trim()) return;
      const currentOffset = newOffset ?? offset;
      setLoading(true);
      setLookupError(null);
      setHasSearched(true);
      try {
        const res = await api.getPaginated(
          `/api/v1/decks/account/${encodeURIComponent(lookupAccountId.trim())}`,
          currentOffset,
          limit
        );
        setDecks(res.items || res.data || res.decks || []);
        setTotal(res.total ?? res.count ?? 0);
        if (newOffset !== undefined) setOffset(newOffset);
      } catch (err) {
        setLookupError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [lookupAccountId, offset]
  );

  function handleSearch(e) {
    e.preventDefault();
    setOffset(0);
    fetchDecks(0);
  }

  function handlePageChange(newOffset) {
    setOffset(newOffset);
    fetchDecks(newOffset);
  }

  const deckColumns = [
    {
      key: 'id',
      label: 'Deck ID',
      render: (val, row) => (
        <span className="font-mono text-xs text-gray-600">{truncate(row.id || row.deck_id)}</span>
      ),
    },
    {
      key: 'slide_count',
      label: 'Slides',
      render: (val, row) => (
        <span className="text-sm font-medium text-gray-800">{row.slide_count ?? '-'}</span>
      ),
    },
    {
      key: 'google_slides_url',
      label: 'Google Slides',
      render: (val, row) => {
        const url = row.google_slides_url || row.slides_url;
        if (!url) return <span className="text-gray-400">-</span>;
        return (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-brand hover:text-brand-dark text-sm font-medium underline"
          >
            Open
          </a>
        );
      },
    },
    {
      key: 'created_at',
      label: 'Generated At',
      render: (val, row) => (
        <span className="text-xs text-gray-500">
          {formatDate(row.created_at || row.generated_at)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      {/* Generate Deck Form */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Generate Deck</h3>
        <form onSubmit={handleGenerate} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Account ID
              </label>
              <input
                type="text"
                value={genAccountId}
                onChange={(e) => setGenAccountId(e.target.value)}
                placeholder="Enter account ID"
                required
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Offering
              </label>
              <select
                value={offering}
                onChange={(e) => setOffering(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              >
                {OFFERINGS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button type="submit" loading={generating}>
            Generate Deck
          </Button>
        </form>

        {/* Error */}
        {genError && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm text-red-700">Failed to generate deck: {genError}</p>
          </div>
        )}

        {/* Generated Deck Result */}
        {generatedDeck && (
          <div className="mt-6 rounded-lg border border-green-200 bg-green-50 p-5">
            <div className="flex items-start gap-3">
              <svg className="w-6 h-6 text-green-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-green-800 mb-2">
                  Deck Generated Successfully
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                  <div>
                    <span className="text-green-700 font-medium">Deck ID: </span>
                    <span className="font-mono text-green-800">
                      {truncate(generatedDeck.id || generatedDeck.deck_id, 20)}
                    </span>
                  </div>
                  <div>
                    <span className="text-green-700 font-medium">Slides: </span>
                    <span className="text-green-800">{generatedDeck.slide_count ?? '-'}</span>
                  </div>
                  <div>
                    <span className="text-green-700 font-medium">Generated: </span>
                    <span className="text-green-800">
                      {formatDate(generatedDeck.created_at || generatedDeck.generated_at)}
                    </span>
                  </div>
                </div>

                {(generatedDeck.google_slides_url || generatedDeck.slides_url) && (
                  <a
                    href={generatedDeck.google_slides_url || generatedDeck.slides_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-dark transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open in Google Slides
                  </a>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Decks by Account */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Decks by Account</h3>
        <form onSubmit={handleSearch} className="flex items-end gap-3 mb-5">
          <div className="flex-1 max-w-sm">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Account ID
            </label>
            <input
              type="text"
              value={lookupAccountId}
              onChange={(e) => setLookupAccountId(e.target.value)}
              placeholder="Search by account ID"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
            />
          </div>
          <Button type="submit" loading={loading}>
            Search
          </Button>
        </form>

        {/* Error */}
        {lookupError && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm text-red-700">Failed to load decks: {lookupError}</p>
          </div>
        )}

        {/* Results */}
        {hasSearched && (
          <>
            <Table
              columns={deckColumns}
              data={decks}
              loading={loading}
              emptyMessage="No decks found for this account."
            />
            <Pagination
              total={total}
              offset={offset}
              limit={limit}
              onChange={handlePageChange}
            />
          </>
        )}
      </div>
    </div>
  );
}
