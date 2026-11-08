import type { Metadata } from "next";
import Link from "next/link";
import TopBar from "@/components/TopBar";
import AthleteView from "@/components/AthleteView";
import { CONTACT_EMAIL } from "@/lib/site";

export async function generateMetadata({ params }: PageProps<"/athlete/[name]">): Promise<Metadata> {
  const { name } = await params;
  return { title: decodeURIComponent(name) };
}

export default async function AthletePage({ params }: PageProps<"/athlete/[name]">) {
  const { name } = await params;
  const athleteName = decodeURIComponent(name);

  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-semibold">{athleteName}</h1>

        <AthleteView name={athleteName} />

        <p className="mt-10 text-xs leading-5 text-black/50 dark:text-white/50">
          Results are matched by name only, so athletes who share a name may appear merged, and one athlete may
          appear under different spellings. Estimates are statistical, not guarantees, and are made at each
          athlete&apos;s last recorded bodyweight. To report an error or ask
          for a result to be corrected or removed, email{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="underline">
            {CONTACT_EMAIL}
          </a>
          . See the{" "}
          <Link href="/privacy" className="underline">
            Privacy Policy
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
