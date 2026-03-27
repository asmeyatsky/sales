const OPTIONS = [
  { value: 'PROFESSIONAL_CONSULTANT', label: 'Professional' },
  { value: 'WITTY_TECH_PARTNER', label: 'Witty' },
];

export default function ToneToggle({ value, onChange }) {
  return (
    <div className="inline-flex rounded-lg bg-gray-100 p-1">
      {OPTIONS.map((opt) => {
        const isActive = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`
              px-4 py-1.5 text-sm font-medium rounded-md transition-all duration-150
              ${
                isActive
                  ? 'bg-brand text-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }
            `}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
