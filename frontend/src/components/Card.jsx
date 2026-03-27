export default function Card({ title, value, subtitle, accent }) {
  return (
    <div
      className={`bg-white rounded-xl shadow-sm border border-gray-200 p-5 ${
        accent ? `border-t-4 ${accent}` : ''
      }`}
    >
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        {title}
      </p>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
      {subtitle && (
        <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
      )}
    </div>
  );
}
