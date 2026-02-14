"use client";

import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function ReactQueryProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [client] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          // Conservative defaults to keep behavior close to pre-Query refactors.
          queries: {
            retry: 0,
            refetchOnWindowFocus: false,
            staleTime: 0,
          },
          mutations: {
            retry: 0,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
