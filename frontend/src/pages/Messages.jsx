import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import Button from '../components/Button';
import Badge from '../components/Badge';
import ToneToggle from '../components/ToneToggle';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CHANNELS = [
  { value: 'EMAIL', label: 'Email' },
  { value: 'LINKEDIN_REQUEST', label: 'LinkedIn Request' },
  { value: 'LINKEDIN_MESSAGE', label: 'LinkedIn Message' },
  { value: 'PHONE_SCRIPT', label: 'Phone Script' },
];

const STEPS = [1, 2, 3, 4, 5];

function channelBadgeVariant(channel) {
  const map = {
    EMAIL: 'info',
    LINKEDIN_REQUEST: 'success',
    LINKEDIN_MESSAGE: 'success',
    PHONE_SCRIPT: 'warning',
  };
  return map[channel] || 'default';
}

function toneBadgeVariant(tone) {
  return tone === 'WITTY_TECH_PARTNER' ? 'warning' : 'info';
}

function toneLabel(tone) {
  return tone === 'WITTY_TECH_PARTNER' ? 'Witty' : 'Professional';
}

function qualityColor(score) {
  if (score == null) return { ring: 'text-gray-300', text: 'text-gray-400', label: '--' };
  if (score >= 0.8) return { ring: 'text-green-500', text: 'text-green-700', label: 'Excellent' };
  if (score >= 0.6) return { ring: 'text-yellow-500', text: 'text-yellow-700', label: 'Good' };
  if (score >= 0.4) return { ring: 'text-orange-500', text: 'text-orange-700', label: 'Fair' };
  return { ring: 'text-red-500', text: 'text-red-700', label: 'Low' };
}

// ---------------------------------------------------------------------------
// Quality Score Ring
// ---------------------------------------------------------------------------

function QualityRing({ score }) {
  const pct = score != null ? Math.round(score * 100) : 0;
  const { ring, text, label } = qualityColor(score);
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative inline-flex items-center justify-center w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r={radius} fill="none" stroke="currentColor" strokeWidth="5" className="text-gray-200" />
          <circle
            cx="40"
            cy="40"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="5"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={ring}
          />
        </svg>
        <span className={`absolute text-lg font-bold ${text}`}>
          {score != null ? `${pct}` : '--'}
        </span>
      </div>
      <span className={`mt-1 text-xs font-medium ${text}`}>{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Messages Page
// ---------------------------------------------------------------------------

export default function Messages() {
  const [searchParams] = useSearchParams();

  // Form state -- prefilled from query params if present
  const [form, setForm] = useState({
    account_id: searchParams.get('account_id') || '',
    stakeholder_id: searchParams.get('stakeholder_id') || '',
    channel: searchParams.get('channel') || 'EMAIL',
    tone: searchParams.get('tone') || 'PROFESSIONAL_CONSULTANT',
    step_number: parseInt(searchParams.get('step') || '1', 10),
  });

  // Generated message state
  const [message, setMessage] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [adjustingTone, setAdjustingTone] = useState(false);
  const [error, setError] = useState(null);

  // Update form when search params change
  useEffect(() => {
    const accountId = searchParams.get('account_id');
    const stakeholderId = searchParams.get('stakeholder_id');
    if (accountId || stakeholderId) {
      setForm((prev) => ({
        ...prev,
        ...(accountId && { account_id: accountId }),
        ...(stakeholderId && { stakeholder_id: stakeholderId }),
      }));
    }
  }, [searchParams]);

  // -----------------------------------------------------------------------
  // Actions
  // -----------------------------------------------------------------------

  const handleGenerate = useCallback(async () => {
    if (!form.account_id.trim() || !form.stakeholder_id.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await api.post('/api/v1/messages/generate', {
        account_id: form.account_id.trim(),
        stakeholder_id: form.stakeholder_id.trim(),
        channel: form.channel,
        tone: form.tone,
        step_number: form.step_number,
      });
      setMessage(res);
    } catch (err) {
      setError(err.message || 'Message generation failed');
    } finally {
      setGenerating(false);
    }
  }, [form]);

  const handlePreview = useCallback(async () => {
    if (!form.account_id.trim() || !form.stakeholder_id.trim()) return;
    setPreviewing(true);
    setError(null);
    try {
      const res = await api.post('/api/v1/messages/preview', {
        account_id: form.account_id.trim(),
        stakeholder_id: form.stakeholder_id.trim(),
        channel: form.channel,
        tone: form.tone,
      });
      setMessage(res);
    } catch (err) {
      setError(err.message || 'Preview failed');
    } finally {
      setPreviewing(false);
    }
  }, [form]);

  const handleAdjustTone = useCallback(async () => {
    if (!message?.message_id) return;
    const newTone =
      message.tone === 'PROFESSIONAL_CONSULTANT'
        ? 'WITTY_TECH_PARTNER'
        : 'PROFESSIONAL_CONSULTANT';
    setAdjustingTone(true);
    setError(null);
    try {
      const res = await api.post(`/api/v1/messages/${message.message_id}/adjust-tone`, {
        new_tone: newTone,
      });
      setMessage(res);
      setForm((prev) => ({ ...prev, tone: newTone }));
    } catch (err) {
      setError(err.message || 'Tone adjustment failed');
    } finally {
      setAdjustingTone(false);
    }
  }, [message]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  const canSubmit = form.account_id.trim() && form.stakeholder_id.trim();

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 min-h-[calc(100vh-8rem)]">
      {/* Left Panel -- Form */}
      <div className="lg:col-span-2">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 sticky top-6">
          <h2 className="text-base font-semibold text-gray-900 mb-5">Generate Message</h2>

          <div className="space-y-4">
            {/* Account ID */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Account ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.account_id}
                onChange={(e) => updateField('account_id', e.target.value)}
                placeholder="acc_..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
            </div>

            {/* Stakeholder ID */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Stakeholder ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.stakeholder_id}
                onChange={(e) => updateField('stakeholder_id', e.target.value)}
                placeholder="stk_..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
            </div>

            {/* Channel */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Channel</label>
              <select
                value={form.channel}
                onChange={(e) => updateField('channel', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              >
                {CHANNELS.map((ch) => (
                  <option key={ch.value} value={ch.value}>
                    {ch.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Tone Toggle */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tone</label>
              <ToneToggle
                value={form.tone}
                onChange={(val) => updateField('tone', val)}
              />
            </div>

            {/* Step Number */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sequence Step
              </label>
              <select
                value={form.step_number}
                onChange={(e) => updateField('step_number', parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              >
                {STEPS.map((s) => (
                  <option key={s} value={s}>
                    Step {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">
                {error}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                loading={generating}
                disabled={!canSubmit}
                onClick={handleGenerate}
                className="flex-1"
              >
                Generate
              </Button>
              <Button
                variant="secondary"
                loading={previewing}
                disabled={!canSubmit}
                onClick={handlePreview}
                className="flex-1"
              >
                Preview
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel -- Preview */}
      <div className="lg:col-span-3">
        {!message ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex items-center justify-center h-full min-h-[400px]">
            <div className="text-center px-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">
                Fill in the form and click <span className="font-medium">Generate</span> or{' '}
                <span className="font-medium">Preview</span> to see your message here.
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            {/* Preview Header */}
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant={channelBadgeVariant(message.channel)}>
                    {message.channel?.replace(/_/g, ' ') || 'EMAIL'}
                  </Badge>
                  <Badge variant={toneBadgeVariant(message.tone)}>
                    {toneLabel(message.tone)}
                  </Badge>
                  {message.status && (
                    <Badge variant="default">{message.status}</Badge>
                  )}
                </div>
                <Button
                  variant="secondary"
                  className="text-xs"
                  loading={adjustingTone}
                  onClick={handleAdjustTone}
                >
                  Adjust Tone
                </Button>
              </div>
            </div>

            {/* Message Content */}
            <div className="p-6">
              <div className="flex gap-6">
                {/* Message text */}
                <div className="flex-1 min-w-0 space-y-4">
                  {/* Subject (email only) */}
                  {message.subject && (
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                        Subject
                      </label>
                      <p className="text-sm font-semibold text-gray-900 bg-gray-50 rounded-lg px-4 py-2.5 border border-gray-200">
                        {message.subject}
                      </p>
                    </div>
                  )}

                  {/* Body */}
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                      Body
                    </label>
                    <div className="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-lg px-4 py-3 border border-gray-200 whitespace-pre-wrap">
                      {message.body}
                    </div>
                  </div>

                  {/* Call to Action */}
                  {message.call_to_action && (
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                        Call to Action
                      </label>
                      <p className="text-sm font-medium text-brand bg-blue-50 rounded-lg px-4 py-2.5 border border-blue-200">
                        {message.call_to_action}
                      </p>
                    </div>
                  )}
                </div>

                {/* Quality Score */}
                <div className="flex-shrink-0">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 text-center">
                    Quality
                  </label>
                  <QualityRing score={message.quality_score} />
                </div>
              </div>

              {/* Message Meta */}
              {(message.company_name || message.stakeholder_name || message.searce_offering) && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                    {message.company_name && (
                      <div>
                        <span className="text-gray-500">Company</span>
                        <p className="font-medium text-gray-900">{message.company_name}</p>
                      </div>
                    )}
                    {message.stakeholder_name && (
                      <div>
                        <span className="text-gray-500">Stakeholder</span>
                        <p className="font-medium text-gray-900">{message.stakeholder_name}</p>
                      </div>
                    )}
                    {message.searce_offering && (
                      <div>
                        <span className="text-gray-500">Offering</span>
                        <p className="font-medium text-gray-900">{message.searce_offering}</p>
                      </div>
                    )}
                    {message.buying_signals && message.buying_signals.length > 0 && (
                      <div>
                        <span className="text-gray-500">Signals Used</span>
                        <p className="font-medium text-gray-900">{message.buying_signals.length}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Footer with message ID */}
            {message.message_id && (
              <div className="px-6 py-3 border-t border-gray-100 bg-gray-50/50">
                <span className="text-xs text-gray-400">
                  Message ID: {message.message_id}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
