import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { UserInputRequestCard } from "@/features/chat/components/execution/chat-panel/user-input-request-card";
import type { UserInputRequest } from "@/features/chat/types";

vi.mock("@/lib/i18n/client", () => ({
  useT: () => ({
    t: (key: string, options?: string | Record<string, unknown>) => {
      if (typeof options === "string") {
        return options;
      }
      if (key === "chat.askUserTimeout") {
        return `Time left ${String(options?.seconds ?? "")}s`;
      }
      return key;
    },
  }),
}));

vi.mock("@/lib/utils/sound", () => ({
  playCompletionSound: vi.fn(),
}));

describe("UserInputRequestCard", () => {
  it("submits answers keyed by question id when present", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    const request: UserInputRequest = {
      id: "req-1",
      session_id: "session-1",
      tool_name: "Bash",
      tool_input: {
        questions: [
          {
            id: "approved",
            header: "Permission required",
            question: "Allow this command to run?",
            multiSelect: false,
            options: [
              {
                label: "Approve",
                value: "true",
                description: "Allow the tool call",
              },
              {
                label: "Reject",
                value: "false",
                description: "Deny the tool call",
              },
            ],
          },
        ],
      },
      status: "pending",
      answers: null,
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    render(<UserInputRequestCard request={request} onSubmit={onSubmit} />);

    await user.click(screen.getByText("Approve"));
    await user.click(screen.getByRole("button", { name: "chat.askUserSubmit" }));

    expect(onSubmit).toHaveBeenCalledWith({ approved: "true" });
  });
});
