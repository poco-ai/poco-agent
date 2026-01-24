"use client";

import { useState } from "react";
import { CardNav } from "./card-nav/CardNav";
import { ConnectorsDialog } from "./connectors/connectors-dialog";
import type { ConnectorType } from "../model/connectors";

/**
 * Connectors Bar Entry Component
 *
 * Displays an expandable card that shows MCP, Skill, and Apps sections
 * Can optionally show connectors dialog
 */
export interface ConnectorsBarProps {
  showDialog?: boolean;
  defaultTab?: ConnectorType;
  forceExpanded?: boolean;
}

export function ConnectorsBar({
  showDialog = false,
  defaultTab = "app",
  forceExpanded = false,
}: ConnectorsBarProps = {}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-4 w-full">
      <CardNav
        triggerText="将您的工具连接到 Poco"
        forceExpanded={forceExpanded}
      />
      {showDialog && (
        <ConnectorsDialog
          open={isOpen}
          onOpenChange={setIsOpen}
          defaultTab={defaultTab}
        />
      )}
    </div>
  );
}
