export default function Pagination({ total, offset, limit, onChange }) {
  const start = Math.min(offset + 1, total);
  const end = Math.min(offset + limit, total);
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  if (total === 0) return null;

  return (
    <div className="flex items-center justify-between mt-4 px-1">
      <p className="text-sm text-gray-500">
        Showing{' '}
        <span className="font-medium text-gray-700">{start}</span>
        {' - '}
        <span className="font-medium text-gray-700">{end}</span>
        {' of '}
        <span className="font-medium text-gray-700">{total}</span>
      </p>

      <div className="flex gap-2">
        <button
          onClick={() => onChange(Math.max(0, offset - limit))}
          disabled={!hasPrev}
          className={`
            px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors
            ${
              hasPrev
                ? 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                : 'border-gray-200 text-gray-300 bg-gray-50 cursor-not-allowed'
            }
          `}
        >
          Prev
        </button>
        <button
          onClick={() => onChange(offset + limit)}
          disabled={!hasNext}
          className={`
            px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors
            ${
              hasNext
                ? 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                : 'border-gray-200 text-gray-300 bg-gray-50 cursor-not-allowed'
            }
          `}
        >
          Next
        </button>
      </div>
    </div>
  );
}
