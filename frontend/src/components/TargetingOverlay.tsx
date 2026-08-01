interface Props {
  label: string;
  onCancel: () => void;
}

export default function TargetingOverlay({ label, onCancel }: Props) {
  return (
    <div className="pointer-events-none fixed inset-x-0 top-16 z-20 flex justify-center">
      <div className="pointer-events-auto flex items-center gap-3 rounded-full border border-amber-500 bg-slate-800 px-4 py-1.5 text-sm text-amber-300 shadow-lg">
        <span>{label}</span>
        <button
          className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-200"
          onClick={onCancel}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
