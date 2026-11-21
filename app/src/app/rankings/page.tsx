import type { Metadata } from "next";
import Link from "next/link";
import FastestImprovers from "@/components/FastestImprovers";
import QPointsLists from "@/components/QPointsLists";
import TopBar from "@/components/TopBar";

export const metadata: Metadata = { title: "Rankings" };

export default function RankingsPage() {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
        <h1 className="mb-6 text-2xl font-semibold">Rankings</h1>
        <QPointsLists />
        <FastestImprovers />
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
