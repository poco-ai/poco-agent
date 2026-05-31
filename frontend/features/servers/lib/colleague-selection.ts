import type {
  ColleagueSelection,
  DrawerState,
} from "@/features/servers/ui/server-workspace-types";

export function getExplicitColleagueSelection(
  drawer: DrawerState,
): ColleagueSelection | null {
  if (drawer.type === "colleague" && drawer.selection) {
    return drawer.selection;
  }
  return null;
}
