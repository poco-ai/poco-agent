import { useState } from "react";
import { Search } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ConnectorDetail } from "./connector-detail";
import { ConnectorCard } from "./connector-card";
import {
  AVAILABLE_CONNECTORS,
  Connector,
  ConnectorType,
} from "../../constants/connectors";
import { useT } from "@/lib/i18n/client";

interface ConnectorsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultTab?: ConnectorType;
  key?: string;
}

/**
 * Connectors dialog with tabs, search, and connector grid
 */
export function ConnectorsDialog({
  open,
  onOpenChange,
  defaultTab = "app",
  key,
}: ConnectorsDialogProps) {
  const { t } = useT("translation");
  const [activeTab, setActiveTab] = useState<ConnectorType>(defaultTab);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(
    null,
  );

  const filteredConnectors = AVAILABLE_CONNECTORS.filter(
    (c) => c.type === activeTab || (activeTab === "app" && c.type === "app"),
  );

  // Reset selection when dialog closes
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setSelectedConnector(null);
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange} key={key}>
      <DialogContent className="max-w-4xl p-0 h-[600px] flex flex-col gap-0 bg-background border-border text-foreground overflow-hidden">
        {selectedConnector ? (
          <ConnectorDetail
            connector={selectedConnector}
            onBack={() => setSelectedConnector(null)}
          />
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <DialogTitle>{t("connectors.title")}</DialogTitle>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* Tabs & Search */}
              <div className="px-6 py-4 pb-2">
                <div className="flex items-center justify-between gap-4">
                  <Tabs
                    value={activeTab}
                    onValueChange={(v) => setActiveTab(v as ConnectorType)}
                    className="w-auto"
                  >
                    <TabsList className="bg-transparent p-0 h-auto gap-2 justify-start">
                      <TabsTrigger
                        value="app"
                        className="rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-muted-foreground data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 hover:text-foreground transition-all"
                      >
                        {t("connectors.apps")}
                      </TabsTrigger>
                      <TabsTrigger
                        value="mcp"
                        className="rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-muted-foreground data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 hover:text-foreground transition-all"
                      >
                        MCP
                      </TabsTrigger>
                      <TabsTrigger
                        value="skill"
                        className="rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-muted-foreground data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 hover:text-foreground transition-all"
                      >
                        Skills
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                  <div className="relative w-64">
                    <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
                    <Input
                      placeholder={t("connectors.search")}
                      className="pl-9 h-9 bg-muted/50 border-border focus-visible:ring-1 focus-visible:ring-primary"
                    />
                  </div>
                </div>
              </div>
              <Separator className="bg-border" />

              <div className="flex-1 w-full overflow-y-auto custom-scrollbar">
                <div className="p-6 grid grid-cols-2 gap-4 pb-20">
                  {filteredConnectors.map((connector) => (
                    <ConnectorCard
                      key={connector.id}
                      connector={connector}
                      isComingSoon={true}
                      onClick={() => setSelectedConnector(connector)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
