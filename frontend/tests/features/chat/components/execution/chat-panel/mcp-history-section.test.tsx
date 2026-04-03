import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { McpHistorySection } from "@/features/chat/components/execution/chat-panel/mcp-history-section";
import { getRunsBySessionAction } from "@/features/chat/actions/query-actions";

vi.mock("@/features/chat/actions/query-actions", () => ({
  getRunsBySessionAction: vi.fn(),
}));

vi.mock(
  "@/features/chat/components/execution/chat-panel/mcp-state-machine-card",
  () => ({
    McpStateMachineCard: ({ runId }: { runId: string }) => (
      <div data-testid="mcp-history-card">{runId}</div>
    ),
  }),
);

describe("McpHistorySection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when MCP history should be hidden", () => {
    render(
      <McpHistorySection sessionId="session-1" sessionTime={null} show={false} />,
    );

    expect(screen.queryByTestId("mcp-history-card")).not.toBeInTheDocument();
  });

  it("renders the history card for the latest run in the session", async () => {
    vi.mocked(getRunsBySessionAction).mockResolvedValue([
      {
        run_id: "run-old",
      },
      {
        run_id: "run-latest",
      },
    ] as never);

    render(
      <McpHistorySection
        sessionId="session-1"
        sessionTime="2026-04-03T10:00:00Z"
        show
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("mcp-history-card")).toHaveTextContent(
        "run-latest",
      );
    });

    expect(getRunsBySessionAction).toHaveBeenCalledWith({
      sessionId: "session-1",
    });
  });
});
