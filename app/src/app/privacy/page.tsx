import type { Metadata } from "next";
import TopBar from "@/components/TopBar";
import { CONTACT_EMAIL, SITE_NAME } from "@/lib/site";

export const metadata: Metadata = { title: "Privacy Policy" };

const LAST_UPDATED = "November 8, 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-2 space-y-3 text-sm leading-6 text-black/80 dark:text-white/80">{children}</div>
    </section>
  );
}

function Email() {
  return (
    <a href={`mailto:${CONTACT_EMAIL}`} className="underline">
      {CONTACT_EMAIL}
    </a>
  );
}

export default function PrivacyPage() {
  return (
    <div className="flex min-h-full flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
        <h1 className="text-2xl font-semibold">Privacy Policy</h1>
        <p className="mt-2 text-sm text-black/60 dark:text-white/60">Last updated: {LAST_UPDATED}</p>

        <p className="mt-6 text-sm leading-6 text-black/80 dark:text-white/80">
          {SITE_NAME} is a website that shows USA weightlifting competition results and progress charts. This
          policy explains what information the site handles. In short: you don&apos;t need an account, the site
          doesn&apos;t ask visitors for personal information, and it doesn&apos;t use advertising or tracking
          cookies.
        </p>

        <Section title="Who we are">
          <p>
            {SITE_NAME} is an independent project. It is not affiliated with, endorsed by, or sponsored by USA
            Weightlifting. You can reach us at <Email />.
          </p>
        </Section>

        <Section title="Information we get from visitors">
          <p>
            There are no accounts, forms, or comment sections, and we don&apos;t ask for your name or email
            address. When you use the site, your browser sends requests to our servers so they can respond:
            for example, the text you type into the search box, the athlete pages you open, and any date or
            bodyweight you enter for an estimate.
          </p>
          <p>
            Our hosting provider automatically records standard technical logs for security and reliability,
            which can include your IP address, browser type, the address requested, and the time of the
            request. We don&apos;t use these logs to identify individual visitors or to build profiles of them.
          </p>
        </Section>

        <Section title="Cookies and similar technologies">
          <p>
            The site does not set cookies. It stores one thing in your browser: whether you chose day or night
            mode with the button in the header, so the site looks the way you left it next time. That setting
            stays on your device and is never sent to us. If you never press the button, nothing is stored and
            the site follows your device&apos;s light or dark setting.
          </p>
          <p>
            To load faster, your browser may keep copies of results it has already downloaded for up to an
            hour, like it does for most websites.
          </p>
          <p>
            To see how the site is used, we use Vercel Web Analytics, which does not use cookies. For each page
            view it records the page, the site you came from, your approximate location, and your browser,
            operating system and device type. Visitors are counted using a code generated from each request
            that resets every day, so you can&apos;t be followed from one day to the next or across other
            websites.
          </p>
          <p>
            The site has no advertising or social-media trackers, and its fonts are served from the site itself
            rather than from a third party. If any of this changes, this page will be updated first.
          </p>
        </Section>

        <Section title="Service providers">
          <p>
            We use Vercel to host the site and measure visits (see above), and Supabase to store the results
            database. They process information
            on our behalf to run the site, and may keep their own technical logs as described above. We do not
            sell personal information, and we do not share it for advertising.
          </p>
        </Section>

        <Section title="If you email us">
          <p>
            If you write to <Email />, we use your message and email address only to respond to you, and keep
            them only as long as needed for that.
          </p>
        </Section>

        <Section title="Corrections and removal requests">
          <p>
            If you spot an error, or you are an athlete (or a parent or guardian) who would like a result
            corrected or removed from the site, email <Email /> with the athlete&apos;s name and enough detail
            to identify the result, such as the meet and date. We will review every request and aim to respond
            within 30 days.
          </p>
        </Section>

        <Section title="Your rights">
          <p>
            Depending on where you live, you may have the right to ask what information we hold about you, to
            have it corrected or deleted, or to object to how it is used. For the competition results on this
            site, use the process above. For anything else, contact <Email />.
          </p>
        </Section>

        <Section title="Security">
          <p>
            We take reasonable steps to protect the site and its data, including keeping the website&apos;s own
            access to the results database read-only. No system is perfectly secure, so we can&apos;t guarantee
            absolute security.
          </p>
        </Section>

        <Section title="Changes to this policy">
          <p>
            We may update this policy from time to time. The &ldquo;Last updated&rdquo; date at the top shows
            when it last changed.
          </p>
        </Section>

        <Section title="Contact">
          <p>
            Questions about this policy or the site: <Email />.
          </p>
        </Section>
      </main>
    </div>
  );
}
