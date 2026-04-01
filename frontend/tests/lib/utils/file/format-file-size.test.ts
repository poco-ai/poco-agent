import { describe, it, expect } from "vitest";
import { formatFileSize } from "@/lib/utils/file/format-file-size";

describe("formatFileSize", () => {
  it('returns "0 B" for zero bytes', () => {
    expect(formatFileSize(0)).toBe("0 B");
  });

  it('returns "1 B" for one byte', () => {
    expect(formatFileSize(1)).toBe("1 B");
  });

  it('returns "1 KB" for 1024 bytes', () => {
    expect(formatFileSize(1024)).toBe("1 KB");
  });

  it('returns "1 MB" for 1048576 bytes', () => {
    expect(formatFileSize(1048576)).toBe("1 MB");
  });

  it('returns "1 GB" for 1073741824 bytes', () => {
    expect(formatFileSize(1073741824)).toBe("1 GB");
  });

  it('returns "1 TB" for 1099511627776 bytes', () => {
    expect(formatFileSize(1099511627776)).toBe("1 TB");
  });

  it('returns "1.5 KB" for 1536 bytes', () => {
    expect(formatFileSize(1536)).toBe("1.5 KB");
  });

  it('returns "2.4 KB" for 2500 bytes', () => {
    expect(formatFileSize(2500)).toBe("2.4 KB");
  });

  it('returns "3.5 MB" for 3670016 bytes', () => {
    expect(formatFileSize(3670016)).toBe("3.5 MB");
  });

  it('returns "500.5 TB" for very large TB value', () => {
    const bytes = 550 * 1024 * 1024 * 1024 * 1024;
    const result = formatFileSize(bytes);
    expect(result).toBe("550 TB");
  });
});
