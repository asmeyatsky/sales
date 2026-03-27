const VARIANTS = {
  primary: 'bg-brand hover:bg-brand-dark text-white shadow-sm',
  secondary: 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 shadow-sm',
  danger: 'bg-red-600 hover:bg-red-700 text-white shadow-sm',
};

function Spinner() {
  return (
    <svg
      className="animate-spin -ml-0.5 mr-2 h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export default function Button({
  variant = 'primary',
  loading = false,
  disabled = false,
  children,
  onClick,
  type = 'button',
  className = '',
}) {
  const base =
    'inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  const variantClasses = VARIANTS[variant] || VARIANTS.primary;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variantClasses} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}
