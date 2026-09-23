import TopBar from "@/components/TopBar";
import GraphControls from "@/components/GraphControls";
import ResultsTable from "@/components/ResultsTable";

export default async function AthletePage({ params }: PageProps<"/athlete/[name]">) {
  const { name } = await params;
  const athleteName = decodeURIComponent(name);

  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-semibold">{athleteName}</h1>

        <div className="mt-6">
          <GraphControls />

          <div className="mt-4 flex h-80 items-center justify-center rounded-xl border border-black/10 text-sm text-black/40 dark:border-white/10 dark:text-white/40">
            Graph will render here once athlete data is wired up.
          </div>
        </div>

        <div className="mt-10">
          <ResultsTable />
        </div>
      </main>
    </div>
  );
}
