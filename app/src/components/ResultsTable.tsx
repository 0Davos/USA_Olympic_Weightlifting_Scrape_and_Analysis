const MOCK_RESULTS = [
  { date: "2026-06-14", meet: "Sample Open", bodyweight: 81.2, bestSn: 120, bestCj: 150, total: 270 },
  { date: "2026-03-02", meet: "Sample Qualifier", bodyweight: 80.4, bestSn: 117, bestCj: 147, total: 264 },
  { date: "2025-11-09", meet: "Sample Classic", bodyweight: 82.0, bestSn: 115, bestCj: 145, total: 260 },
];

export default function ResultsTable() {
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
        {MOCK_RESULTS.map((r) => (
          <tr key={r.date} className="border-b border-black/5 dark:border-white/5">
            <td className="py-2 pr-4">{r.date}</td>
            <td className="py-2 pr-4">{r.meet}</td>
            <td className="py-2 pr-4">{r.bodyweight}</td>
            <td className="py-2 pr-4">{r.bestSn}</td>
            <td className="py-2 pr-4">{r.bestCj}</td>
            <td className="py-2 pr-4">{r.total}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
