import Link from "next/link";
import TopBar from "@/components/TopBar";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <div className="grid gap-6 sm:grid-cols-2">
          <section className="rounded-xl border border-black/10 p-6 dark:border-white/10">
            <h2 className="text-lg font-semibold">Top Men — Q-points</h2>
            <p className="mt-2 text-sm text-black/50 dark:text-white/50">Coming soon.</p>
          </section>

          <section className="rounded-xl border border-black/10 p-6 dark:border-white/10">
            <h2 className="text-lg font-semibold">Top Women — Q-points</h2>
            <p className="mt-2 text-sm text-black/50 dark:text-white/50">Coming soon.</p>
          </section>
        </div>
      </main>

      <footer className="border-t border-black/10 px-4 py-6 dark:border-white/10">
        <div className="mx-auto flex max-w-5xl gap-6 text-sm text-black/60 dark:text-white/60">
          <Link href="/about" className="hover:underline">About</Link>
          <Link href="/privacy" className="hover:underline">Privacy Policy</Link>
        </div>
      </footer>
    </div>
  );
}
