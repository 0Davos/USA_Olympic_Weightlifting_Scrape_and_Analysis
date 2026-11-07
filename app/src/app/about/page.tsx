import type { Metadata } from "next";
import TopBar from "@/components/TopBar";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-semibold">About</h1>
        <p className="mt-4 text-sm text-black/60 dark:text-white/60">Coming soon.</p>
      </main>
    </div>
  );
}
