import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  copyToClipboard,
  readFromClipboard,
} from "@/lib/utils/clipboard/copy-to-clipboard";

describe("copyToClipboard", () => {
  let mockWriteText: ReturnType<typeof vi.fn>;
  let mockReadText: ReturnType<typeof vi.fn>;
  let originalDocument: Document;

  beforeEach(() => {
    // Store original document
    originalDocument = global.document;

    mockWriteText = vi.fn().mockResolvedValue(undefined);
    mockReadText = vi.fn().mockResolvedValue("clipboard content");
    Object.defineProperty(navigator, "clipboard", {
      writable: true,
      value: {
        writeText: mockWriteText,
        readText: mockReadText,
      },
    });
    Object.defineProperty(window, "isSecureContext", {
      writable: true,
      value: true,
    });
  });

  afterEach(() => {
    // Restore document
    global.document = originalDocument;
  });

  describe("Clipboard API path", () => {
    it("copies text using Clipboard API when available", async () => {
      const result = await copyToClipboard("test text");
      expect(result).toBe(true);
      expect(mockWriteText).toHaveBeenCalledWith("test text");
    });

    it("calls onSuccess callback on success", async () => {
      const onSuccess = vi.fn();
      await copyToClipboard("test text", { onSuccess });
      expect(onSuccess).toHaveBeenCalled();
    });

    it("does not call onError on success", async () => {
      const onError = vi.fn();
      await copyToClipboard("test text", { onError });
      expect(onError).not.toHaveBeenCalled();
    });
  });

  describe("fallback path", () => {
    beforeEach(() => {
      Object.defineProperty(navigator, "clipboard", {
        writable: true,
        value: null,
      });
    });

    it("falls back to execCommand when Clipboard API unavailable", async () => {
      // Define execCommand on document for this test
      Object.defineProperty(document, "execCommand", {
        writable: true,
        value: vi.fn(() => true),
      });

      const mockTextArea = document.createElement("textarea");
      mockTextArea.value = "";
      vi.spyOn(mockTextArea, "focus").mockImplementation(() => {});
      vi.spyOn(mockTextArea, "select").mockImplementation(() => {});

      vi.spyOn(document, "createElement").mockReturnValue(mockTextArea);
      vi.spyOn(document.body, "appendChild").mockImplementation(
        () => mockTextArea,
      );
      vi.spyOn(document.body, "removeChild").mockImplementation(
        (node: Node) => node,
      );

      const result = await copyToClipboard("fallback text");
      expect(result).toBe(true);
      expect(mockTextArea.value).toBe("fallback text");
    });

    it("calls onSuccess on fallback success", async () => {
      Object.defineProperty(document, "execCommand", {
        writable: true,
        value: vi.fn(() => true),
      });

      const mockTextArea = document.createElement("textarea");
      mockTextArea.value = "";
      vi.spyOn(mockTextArea, "focus").mockImplementation(() => {});
      vi.spyOn(mockTextArea, "select").mockImplementation(() => {});

      vi.spyOn(document, "createElement").mockReturnValue(mockTextArea);
      vi.spyOn(document.body, "appendChild").mockImplementation(
        () => mockTextArea,
      );
      vi.spyOn(document.body, "removeChild").mockImplementation(
        (node: Node) => node,
      );

      const onSuccess = vi.fn();
      await copyToClipboard("fallback text", { onSuccess });
      expect(onSuccess).toHaveBeenCalled();
    });

    it("returns false when execCommand fails", async () => {
      Object.defineProperty(document, "execCommand", {
        writable: true,
        value: vi.fn(() => false),
      });

      const mockTextArea = document.createElement("textarea");
      mockTextArea.value = "";
      vi.spyOn(mockTextArea, "focus").mockImplementation(() => {});
      vi.spyOn(mockTextArea, "select").mockImplementation(() => {});

      vi.spyOn(document, "createElement").mockReturnValue(mockTextArea);
      vi.spyOn(document.body, "appendChild").mockImplementation(
        () => mockTextArea,
      );
      vi.spyOn(document.body, "removeChild").mockImplementation(
        (node: Node) => node,
      );

      const onError = vi.fn();
      const result = await copyToClipboard("fallback text", { onError });
      expect(result).toBe(false);
      expect(onError).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("returns false and calls onError when Clipboard API throws", async () => {
      mockWriteText.mockRejectedValue(new Error("Permission denied"));
      const onError = vi.fn();
      const result = await copyToClipboard("test", { onError });
      expect(result).toBe(false);
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: "Permission denied" }),
      );
    });

    it("handles non-Error errors", async () => {
      mockWriteText.mockRejectedValue("string error");
      const onError = vi.fn();
      await copyToClipboard("test", { onError });
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({ message: "string error" }),
      );
    });
  });

  describe("SSR behavior", () => {
    it("returns false when window is undefined", async () => {
      const originalWindow = global.window;
      // @ts-expect-error - intentionally removing window for SSR test
      delete global.window;

      const result = await copyToClipboard("test");
      expect(result).toBe(false);

      global.window = originalWindow;
    });
  });
});

describe("readFromClipboard", () => {
  let mockReadText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockReadText = vi.fn();
    Object.defineProperty(navigator, "clipboard", {
      writable: true,
      value: {
        readText: mockReadText,
      },
    });
    Object.defineProperty(window, "isSecureContext", {
      writable: true,
      value: true,
    });
  });

  it("reads text from clipboard", async () => {
    mockReadText.mockResolvedValue("clipboard content");
    const result = await readFromClipboard();
    expect(result).toBe("clipboard content");
    expect(mockReadText).toHaveBeenCalled();
  });

  it("returns null when clipboard API throws", async () => {
    mockReadText.mockRejectedValue(new Error("Permission denied"));
    const result = await readFromClipboard();
    expect(result).toBeNull();
  });

  it("returns null when not in secure context", async () => {
    Object.defineProperty(window, "isSecureContext", {
      writable: true,
      value: false,
    });
    const result = await readFromClipboard();
    expect(result).toBeNull();
  });

  it("returns null when window is undefined (SSR)", async () => {
    const originalWindow = global.window;
    // @ts-expect-error - intentionally removing window for SSR test
    delete global.window;

    const result = await readFromClipboard();
    expect(result).toBeNull();

    global.window = originalWindow;
  });

  it("returns null when navigator.clipboard is unavailable", async () => {
    Object.defineProperty(navigator, "clipboard", {
      writable: true,
      value: null,
    });
    const result = await readFromClipboard();
    expect(result).toBeNull();
  });
});
