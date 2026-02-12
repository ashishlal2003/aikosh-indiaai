import { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle, Clock, XCircle, Circle } from 'lucide-react';

const REQUIRED_DOCS = [
  { key: 'invoice', label: 'Invoice', desc: 'Proof of goods/services delivered' },
  { key: 'purchase_order', label: 'Purchase Order', desc: 'Contract or PO agreement' },
  { key: 'delivery_proof', label: 'Delivery Proof', desc: 'Receipt or acknowledgment' },
  { key: 'msme_certificate', label: 'MSME Certificate', desc: 'Udyam registration' },
];

const OPTIONAL_DOCS = [
  { key: 'communication', label: 'Communication Trail (Optional)', desc: 'Emails/messages with buyer' },
];

const STATUS_CONFIG = {
  verified: {
    icon: CheckCircle,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    label: 'Verified',
  },
  pending: {
    icon: Clock,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    label: 'Uploaded',
  },
  rejected: {
    icon: XCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    label: 'Rejected',
  },
  missing: {
    icon: Circle,
    color: 'text-gray-500',
    bg: 'bg-white/5',
    border: 'border-white/10',
    label: 'Missing',
  },
};

export default function ClaimProgress({ completeness }) {
  const [expanded, setExpanded] = useState(false);

  if (!completeness) return null;

  const { completeness_percentage, verified_count, total_required, per_document } = completeness;
  const pct = Math.round(completeness_percentage || 0);

  const barColor =
    pct === 100 ? 'bg-green-500' : pct >= 60 ? 'bg-gradient-to-r from-orange-500 to-pink-500' : pct >= 20 ? 'bg-amber-500' : 'bg-gray-600';

  return (
    <div className="border-b border-white/10 bg-white/5 backdrop-blur-lg">
      {/* Collapsed summary row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/10 transition-all duration-300 text-left"
        aria-label={expanded ? 'Collapse claim progress' : 'Expand claim progress'}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
              Claim Completeness
            </span>
            <span className={`text-xs font-bold ${pct === 100 ? 'text-green-400' : 'text-gray-200'}`}>
              {verified_count}/{total_required} verified · {pct}%
            </span>
          </div>
          <div className="w-full bg-white/10 rounded-full h-2.5 overflow-hidden backdrop-blur-lg">
            <div
              className={`h-2.5 rounded-full transition-all duration-500 ${barColor} ${pct === 100 ? 'shadow-lg shadow-green-500/30' : ''}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
        <div className="flex-shrink-0 text-gray-400">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded doc list */}
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {REQUIRED_DOCS.map((doc) => {
            const status = per_document?.[doc.key] || 'missing';
            const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.missing;
            const Icon = cfg.icon;

            return (
              <div
                key={doc.key}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border ${cfg.bg} ${cfg.border} backdrop-blur-lg transition-all duration-300`}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 ${cfg.color}`} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-gray-200">{doc.label}</span>
                  <span className="text-xs text-gray-400 ml-1.5">{doc.desc}</span>
                </div>
                <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
              </div>
            );
          })}

          {/* Optional docs */}
          {OPTIONAL_DOCS.map((doc) => {
            const status = per_document?.[doc.key] || 'missing';
            const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.missing;
            const Icon = cfg.icon;

            return (
              <div
                key={doc.key}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border ${cfg.bg} ${cfg.border} opacity-60 backdrop-blur-lg`}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 ${cfg.color}`} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-gray-200">{doc.label}</span>
                  <span className="text-xs text-gray-400 ml-1.5">{doc.desc}</span>
                </div>
                <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
              </div>
            );
          })}

          {pct === 100 && (
            <div className="mt-2 px-3 py-2.5 bg-green-500/10 border border-green-500/30 rounded-xl text-sm text-green-400 font-medium text-center backdrop-blur-lg">
              ✨ All required documents verified — ready to send demand notice!
            </div>
          )}
        </div>
      )}
    </div>
  );
}
