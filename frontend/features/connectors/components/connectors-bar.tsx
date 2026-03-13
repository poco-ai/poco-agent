"use client";

import { useState } from "react";
import { CardNav } from "./card-nav/card-nav";
import { ConnectorsDialog } from "./connectors/connectors-dialog";
import type { ConnectorType } from "../constants/connectors";

/**
 * Connectors Bar Entry Component
 *
 * Displays a connectors entry row that opens MCP/Skill/Plugin controls in a dialog
 * Can optionally show connectors dialog
 */
export interface ConnectorsBarProps {
  showDialog?: boolean;
  defaultTab?: ConnectorType;
}

export function ConnectorsBar({
  showDialog = false,
  defaultTab = "app",
}: ConnectorsBarProps = {}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  if (!isVisible) return null;

  return (
    <div className="w-full">
      <CardNav embedded showDismiss onDismiss={() => setIsVisible(false)} />
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
