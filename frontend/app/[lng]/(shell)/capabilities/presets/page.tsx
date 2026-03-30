import { redirect } from "next/navigation";

interface CapabilitiesPresetsPageProps {
  params: Promise<{
    lng: string;
  }>;
}

export default async function CapabilitiesPresetsPage({
  params,
}: CapabilitiesPresetsPageProps) {
  const { lng } = await params;
  redirect(`/${lng}/presets`);
}
