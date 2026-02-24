export const SIDEBAR_CARD_BASE_CLASS =
  "h-[36px] min-w-0 w-full max-w-[calc(var(--sidebar-width)-16px)] justify-start gap-3 rounded-[10px] px-3 py-[7.5px] text-left text-muted-foreground transition-colors hover:bg-sidebar-accent overflow-hidden group-data-[collapsible=icon]:w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:max-w-[var(--sidebar-width-icon)] group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0";

export const SIDEBAR_CARD_WITH_ACTION_CLASS = `${SIDEBAR_CARD_BASE_CLASS} pr-8 group-data-[collapsible=icon]:pr-0`;

export const SIDEBAR_CARD_TEXT_CLASS =
  "flex-1 min-w-0 truncate text-sm group-data-[collapsible=icon]:hidden";

export const SIDEBAR_CARD_NESTED_INSET_CLASS =
  "pl-6 group-data-[collapsible=icon]:pl-0";
