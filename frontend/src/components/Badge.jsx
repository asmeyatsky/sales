const VARIANTS = {
  success: 'bg-green-100 text-green-700 ring-green-600/20',
  warning: 'bg-yellow-100 text-yellow-700 ring-yellow-600/20',
  danger: 'bg-red-100 text-red-700 ring-red-600/20',
  info: 'bg-blue-100 text-blue-700 ring-blue-600/20',
  default: 'bg-gray-100 text-gray-700 ring-gray-600/20',
};

export default function Badge({ variant = 'default', children }) {
  const classes = VARIANTS[variant] || VARIANTS.default;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset ${classes}`}
    >
      {children}
    </span>
  );
}
