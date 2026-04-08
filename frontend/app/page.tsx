import { redirect } from "next/navigation";
import { fallbackLng } from "@/lib/i18n/settings";

export default function Home() {
  redirect(`/${fallbackLng}`);
}
