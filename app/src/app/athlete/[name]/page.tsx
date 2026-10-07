import TopBar from "@/components/TopBar";
import AthleteView from "@/components/AthleteView";

export default async function AthletePage({ params }: PageProps<"/athlete/[name]">) {
  const { name } = await params;
  const athleteName = decodeURIComponent(name);

  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-semibold">{athleteName}</h1>

        <AthleteView name={athleteName} />
      </main>
    </div>
  );
}
