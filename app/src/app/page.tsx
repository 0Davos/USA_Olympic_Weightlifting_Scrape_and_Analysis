import Link from "next/link";
import HomeCards from "@/components/HomeCards";
import TopBar from "@/components/TopBar";
import { CONTACT_EMAIL } from "@/lib/site";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <h1 className="mb-8 text-2xl font-semibold sm:text-3xl">A full exploration of US Olympic Weightlifting data.</h1>

        <HomeCards />

        <section className="mt-10 text-xs leading-5 text-black/50 dark:text-white/50">
          <h2 className="mb-1 font-semibold">About the data</h2>
          <p>
            Results come from the USA Weightlifting website and cover every athlete from 2012 onward. Results are
            matched by name only, so athletes who share a name may appear merged, and one athlete may appear under
            different spellings. Predictions are statistical estimates, not guarantees. To report an error or ask for a
            result to be corrected, email{" "}
            <a href={`mailto:${CONTACT_EMAIL}`} className="underline">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </section>
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
