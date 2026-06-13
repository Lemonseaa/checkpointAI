type StatusBadgeProps = {
  value: string;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value.toLowerCase();
  const tone =
    normalized.includes("fail") || normalized.includes("error") || normalized.includes("unhealthy")
      ? "border-red-200 bg-red-50 text-red-700"
      : normalized.includes("archive") ||
          normalized.includes("pending") ||
          normalized.includes("degraded") ||
          normalized.includes("fixture") ||
          normalized.includes("synthetic") ||
          normalized.includes("inconclusive")
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : "border-emerald-200 bg-emerald-50 text-emerald-700";
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${tone}`}>
      {value}
    </span>
  );
}
