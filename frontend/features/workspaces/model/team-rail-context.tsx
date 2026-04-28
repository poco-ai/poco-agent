"use client";

import * as React from "react";

interface TeamRailContextValue {
  railContent: React.ReactNode;
  setRailContent: React.Dispatch<React.SetStateAction<React.ReactNode>>;
}

const TeamRailContext = React.createContext<TeamRailContextValue | null>(null);

export function TeamRailProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [railContent, setRailContent] = React.useState<React.ReactNode>(null);

  const value = React.useMemo(
    () => ({
      railContent,
      setRailContent,
    }),
    [railContent],
  );

  return (
    <TeamRailContext.Provider value={value}>
      {children}
    </TeamRailContext.Provider>
  );
}

export function useTeamRailContext(): TeamRailContextValue {
  const value = React.useContext(TeamRailContext);
  if (!value) {
    throw new Error("useTeamRailContext must be used within TeamRailProvider");
  }
  return value;
}
