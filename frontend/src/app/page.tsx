import Link from "next/link";
import { Activity, Globe, Scan, Bug, Gauge, Inbox } from "lucide-react";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { BobStub } from "@/components/ui/bob-stub";

const FEATURES = [
  {
    href: "/regions",
    Icon: Globe,
    title: "Region Atlas",
    description: "Versioned region profiles with semantic-aware diff.",
  },
  {
    href: "/jjscan",
    Icon: Scan,
    title: "JJSCAN+",
    description: "JCL static analysis with reason-tagged dispositions.",
  },
  {
    href: "/abend",
    Icon: Bug,
    title: "ABEND Archaeologist",
    description: "SYSLOG + source triangulation with confidence tiers.",
  },
  {
    href: "/confidence",
    Icon: Gauge,
    title: "Confidence Score",
    description: "0–100 readiness gauge composed across the other three.",
  },
  {
    href: "/review",
    Icon: Inbox,
    title: "Review Queue",
    description: "Real-time team approval with mobile fallback.",
  },
];

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="The four pillars + the queue that ties them together. Click a tile to drill in."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ href, Icon, title, description }) => (
          <Link key={href} href={href} className="block">
            <Card className="h-full transition-transform hover:-translate-y-0.5">
              <CardHeader>
                <Icon className="size-6 text-accent" />
                <CardTitle>{title}</CardTitle>
                <CardDescription>{description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      <h2 className="mb-3 mt-10 flex items-center gap-2 text-lg font-semibold">
        <Activity className="size-5 text-accent" />
        Confidence Score summary
      </h2>
      <BobStub
        feature="Dashboard confidence summary tile"
        spec="Aggregate the three pillars into a single 0–100 readiness gauge for the active shop. Use the gauge component from /confidence."
      />
    </>
  );
}
