import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges multiple class names", () => {
    expect(cn("px-4", "py-2", "bg-blue-500")).toBe("px-4 py-2 bg-blue-500");
  });

  it("handles conditional classes with clsx syntax", () => {
    expect(cn("base-class", true && "conditional", false && "removed")).toBe(
      "base-class conditional",
    );
  });

  it("handles array inputs", () => {
    expect(cn(["class1", "class2"])).toBe("class1 class2");
  });

  it("handles object inputs with conditional classes", () => {
    expect(
      cn({
        "class-a": true,
        "class-b": false,
        "class-c": true,
      }),
    ).toBe("class-a class-c");
  });

  it("resolves Tailwind conflicts with twMerge - later class wins", () => {
    // px-4 and px-6 conflict - px-6 should win
    expect(cn("px-4", "px-6")).toBe("px-6");
  });

  it("resolves multiple Tailwind conflicts", () => {
    // Multiple conflicts: padding and margin
    expect(cn("px-4 py-2", "px-6 py-4")).toBe("px-6 py-4");
  });

  it("handles color conflicts correctly", () => {
    // bg-red-500 should override bg-blue-500
    expect(cn("bg-blue-500", "bg-red-500")).toBe("bg-red-500");
  });

  it("handles responsive variant conflicts", () => {
    // sm:px-4 and px-6 are different breakpoints - both should be kept
    expect(cn("px-4", "sm:px-6")).toBe("px-4 sm:px-6");
  });

  it("handles empty inputs", () => {
    expect(cn()).toBe("");
    expect(cn("")).toBe("");
  });

  it("filters out undefined values", () => {
    expect(cn("class1", undefined, "class2")).toBe("class1 class2");
  });

  it("filters out null values", () => {
    expect(cn("class1", null, "class2")).toBe("class1 class2");
  });

  it("filters out false values in object syntax", () => {
    expect(
      cn({
        "always-include": true,
        "never-include": false,
      }),
    ).toBe("always-include");
  });

  it("handles complex nested inputs", () => {
    expect(
      cn(
        "base",
        ["array1", "array2"],
        { "obj-true": true, "obj-false": false },
        null,
        undefined,
      ),
    ).toBe("base array1 array2 obj-true");
  });

  it("handles numbers as class names", () => {
    expect(cn(1, 2)).toBe("1 2");
  });

  it("merges class names correctly", () => {
    // clsx and twMerge work together to clean up classes
    expect(cn("class1", "class2")).toBe("class1 class2");
  });

  it("handles Tailwind arbitrary values", () => {
    expect(cn("[padding:10px]", "[margin:5px]")).toBe(
      "[padding:10px] [margin:5px]",
    );
  });

  it("handles dark mode variants", () => {
    expect(cn("text-white", "dark:text-gray-900")).toBe(
      "text-white dark:text-gray-900",
    );
  });

  it("handles hover/active/focus variants", () => {
    expect(cn("bg-blue-500", "hover:bg-blue-600", "active:bg-blue-700")).toBe(
      "bg-blue-500 hover:bg-blue-600 active:bg-blue-700",
    );
  });
});
