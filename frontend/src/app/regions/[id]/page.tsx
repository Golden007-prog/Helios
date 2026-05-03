import RegionDetailClient from "./client";

export const dynamicParams = true;

export function generateStaticParams() {
  return [{ id: "placeholder" }];
}

export default function RegionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <RegionDetailClient id={params.id} />;
}
