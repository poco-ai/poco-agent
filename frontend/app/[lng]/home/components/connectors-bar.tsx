"use client";

import * as React from "react";
import { Plug, Plus, Search, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

import {
  MOCK_CONNECTORS,
  Connector,
  ConnectorType,
  ConnectorIcons,
} from "../model/connectors";

export { type Connector, type ConnectorType }; // Re-export if needed, or just let consumers import from model

export function ConnectorsBar() {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <>
      <div
        className="mt-4 flex w-full items-center justify-between rounded-lg border border-border bg-card/50 px-4 py-3 cursor-pointer hover:bg-accent/50 transition-colors group"
        onClick={() => setIsOpen(true)}
      >
        <div className="flex items-center gap-3 text-muted-foreground group-hover:text-foreground transition-colors">
          <Plug className="size-5" />
          <span className="text-sm">将您的工具连接到 OpenCoWork</span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar mask-gradient-right">
          {[
            ConnectorIcons.gmail,
            ConnectorIcons.calendar,
            ConnectorIcons.drive,
            ConnectorIcons.slack,
            ConnectorIcons.github,
            ConnectorIcons.notion,
          ].map((Icon, i) => (
            <div
              key={i}
              className="flex size-6 shrink-0 items-center justify-center rounded-sm bg-muted text-muted-foreground"
            >
              <Icon className="size-3.5" />
            </div>
          ))}
        </div>
      </div>

      <ConnectorsDialog open={isOpen} onOpenChange={setIsOpen} />
    </>
  );
}

function ConnectorsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [activeTab, setActiveTab] = React.useState<ConnectorType>("app");
  const [selectedConnector, setSelectedConnector] =
    React.useState<Connector | null>(null);

  const filteredConnectors = MOCK_CONNECTORS.filter(
    (c) => c.type === activeTab || (activeTab === "app" && c.type === "app"),
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl p-0 h-[600px] flex flex-col gap-0 bg-[#1e1e1e] border-[#333] text-foreground overflow-hidden">
        {selectedConnector ? (
          <ConnectorDetail
            connector={selectedConnector}
            onBack={() => setSelectedConnector(null)}
          />
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#333]">
              <h2 className="text-lg font-semibold">连接器</h2>
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
                        应用
                      </TabsTrigger>
                      <TabsTrigger
                        value="mcp"
                        className="rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-muted-foreground data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 hover:text-foreground transition-all"
                      >
                        自定义 MCP
                      </TabsTrigger>
                      <TabsTrigger
                        value="skill"
                        className="rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-muted-foreground data-[state=active]:bg-primary/10 data-[state=active]:text-primary data-[state=active]:border-primary/20 hover:text-foreground transition-all"
                      >
                        Skill
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                  <div className="relative w-64">
                    <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
                    <Input
                      placeholder="搜索"
                      className="pl-9 h-9 bg-[#252525] border-[#333] focus-visible:ring-1 focus-visible:ring-primary"
                    />
                  </div>
                </div>
              </div>
              <Separator className="bg-[#333]" />

              {/* Grid */}
              <div className="flex-1 w-full overflow-y-auto">
                <div className="p-6 grid grid-cols-2 gap-4 pb-20">
                  {filteredConnectors.map((connector) => {
                    const isAppAndNotGithub =
                      connector.type === "app" && connector.id !== "github";

                    return (
                      <div
                        key={connector.id}
                        className={cn(
                          "flex items-start gap-4 p-4 rounded-xl border border-[#333] bg-[#252525] transition-colors",
                          isAppAndNotGithub
                            ? "opacity-50 cursor-not-allowed"
                            : "hover:bg-[#2a2a2a] cursor-pointer",
                        )}
                        onClick={() => {
                          if (!isAppAndNotGithub) {
                            setSelectedConnector(connector);
                          }
                        }}
                      >
                        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[#333]">
                          <connector.icon className="size-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <div className="font-medium truncate">
                              {connector.title}
                            </div>
                            {isAppAndNotGithub && (
                              <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground whitespace-nowrap">
                                敬请期待
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-muted-foreground line-clamp-2">
                            {connector.description}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ConnectorDetail({
  connector,
  onBack,
}: {
  connector: Connector;
  onBack: () => void;
}) {
  return (
    <div className="flex-1 flex flex-col h-full animate-in fade-in slide-in-from-right-4 duration-200">
      {/* Back button area handled by positioning absolute or just header */}
      <div className="relative flex-1 flex flex-col items-center justify-center p-8 text-center">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="size-5" />
        </Button>

        <div className="mb-6 flex size-24 items-center justify-center rounded-2xl bg-[#252525] border border-[#333]">
          <connector.icon className="size-12" />
        </div>

        <h2 className="text-2xl font-bold mb-4">{connector.title}</h2>
        <p className="text-muted-foreground max-w-md mb-8">
          {connector.description}
        </p>

        <Button className="h-10 px-8 rounded-full bg-white text-black hover:bg-gray-200 font-medium">
          <Plus className="mr-2 size-4" />
          连接
        </Button>
      </div>

      <div className="border-t border-[#333] p-6">
        <div className="grid grid-cols-1 gap-4 text-sm">
          <div className="flex justify-between items-center py-2 border-b border-[#333]/50">
            <span className="text-muted-foreground">连接器类型</span>
            <span className="capitalize">
              {connector.type === "app"
                ? "应用"
                : connector.type === "mcp"
                  ? "MCP"
                  : "Skill"}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#333]/50">
            <span className="text-muted-foreground">作者</span>
            <span>{connector.author}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#333]/50">
            <span className="text-muted-foreground">UUID</span>
            <span className="font-mono text-xs text-muted-foreground flex items-center gap-2">
              f2a3...b9c1{" "}
              <span className="cursor-pointer hover:text-foreground">📄</span>
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#333]/50">
            <span className="text-muted-foreground">网站</span>
            <a
              href={connector.website}
              target="_blank"
              rel="noreferrer"
              className="text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              Link ↗
            </a>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-muted-foreground">隐私政策</span>
            <a
              href={connector.privacyPolicy}
              target="_blank"
              rel="noreferrer"
              className="text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              Link ↗
            </a>
          </div>
        </div>
        <div className="mt-8 text-center">
          <Button
            variant="link"
            className="text-muted-foreground h-auto p-0 text-xs"
          >
            提供反馈
          </Button>
        </div>
      </div>
    </div>
  );
}
