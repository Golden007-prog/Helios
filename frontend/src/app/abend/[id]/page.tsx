import AbendDetailClient from "./client";

export const dynamicParams = true;

export function generateStaticParams() {
  return [{ id: "placeholder" }];
}

export default function AbendDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <AbendDetailClient id={params.id} />;
}
