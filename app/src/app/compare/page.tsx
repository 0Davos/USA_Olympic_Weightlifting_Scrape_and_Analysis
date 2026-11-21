import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import CompareView, { COMPARE_PLACEHOLDER_CLASS } from "@/components/CompareView";
import TopBar from "@/components/TopBar";
import { CONTACT_EMAIL } from "@/lib/site";

export const metadata: Metadata = { title: "Compare" };

export default function ComparePage() {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-semibold">Compare</h1>

        {/* CompareView reads the athletes from the URL, which isn't known while the page is prerendered. */}
        <Suspense fallback={<div className={`mt-6 ${COMPARE_PLACEHOLDER_CLASS}`}>Loading...</div>}>
          <CompareView />
        </Suspense>

        <p className="mt-10 text-xs leading-5 text-black/50 dark:text-white/50">
          Results are matched by name only, so athletes who share a name may appear merged, and one athlete may
          appear under different spellings. Estimates are statistical, not guarantees, and are made at each
          athlete&apos;s last recorded bodyweight. To report an error or ask for a result to be corrected or
          removed, email{" "}
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

      <footer className="border-t border-black/10 px-4 py-6 dark:border-white/10">
        <div className="mx-auto flex max-w-5xl gap-6 text-sm text-black/60 dark:text-white/60">
          <Link href="/about" className="hover:underline">About</Link>
          <Link href="/privacy" className="hover:underline">Privacy Policy</Link>
        </div>
      </footer>
    </div>
  );
}
