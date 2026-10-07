import type { Meet } from "@/lib/athlete";

function show(value: number | null) {
  return value == null ? "—" : value;
}

// Newest first; meets with no date go last.
function newestFirst(rows: Meet[]) {
  return [...rows].sort((a, b) => {
    if (a.date === b.date) return 0;
    if (!a.date) return 1;
    if (!b.date) return -1;
    return a.date < b.date ? 1 : -1;
  });
}

export default function ResultsTable({ rows }: { rows: Meet[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-black/50 dark:text-white/50">No meets in this date range.</p>;
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-black/10 text-left text-black/50 dark:border-white/10 dark:text-white/50">
          <th className="py-2 pr-4 font-medium">Date</th>
          <th className="py-2 pr-4 font-medium">Meet</th>
          <th className="py-2 pr-4 font-medium">Bodyweight</th>
          <th className="py-2 pr-4 font-medium">Best Sn</th>
          <th className="py-2 pr-4 font-medium">Best Cj</th>
          <th className="py-2 pr-4 font-medium">Total</th>
        </tr>
      </thead>
      <tbody>
        {newestFirst(rows).map((r, i) => (
          <tr
            key={`${r.date}-${r.meet}-${i}`}
            className={`border-b border-black/5 dark:border-white/5 ${r.bombed_out ? "text-black/50 dark:text-white/50" : ""}`}
          >
            <td className="py-2 pr-4">{r.date ?? "—"}</td>
            <td className="py-2 pr-4">{r.meet}</td>
            <td className="py-2 pr-4">{show(r.bodyweight)}</td>
            {/* A bomb-out's best lifts are 0 when that lift was missed entirely */}
            <td className="py-2 pr-4">{r.bombed_out && !r.best_sn ? "—" : show(r.best_sn)}</td>
            <td className="py-2 pr-4">{r.bombed_out && !r.best_cj ? "—" : show(r.best_cj)}</td>
            <td className="py-2 pr-4">{r.bombed_out ? "DNF" : show(r.total)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
