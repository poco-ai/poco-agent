import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  describe("basic rendering", () => {
    it("should render with data-slot attribute", () => {
      render(<Button>Click me</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("data-slot", "button");
    });

    it("should render children text", () => {
      render(<Button>Submit</Button>);
      const button = screen.getByRole("button", { name: "Submit" });
      expect(button).toBeInTheDocument();
    });

    it("should render with default variant and size attributes", () => {
      render(<Button>Default</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("data-variant", "default");
      expect(button).toHaveAttribute("data-size", "default");
    });
  });

  describe("variant prop", () => {
    it.each([
      "default",
      "destructive",
      "outline",
      "secondary",
      "ghost",
      "link",
    ] as const)("should render variant: %s", (variant) => {
      render(<Button variant={variant}>Test</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("data-variant", variant);
    });

    it("should apply variant-specific CSS classes", () => {
      const { rerender } = render(<Button variant="default">Default</Button>);
      let button = screen.getByRole("button");
      expect(button).toHaveClass("bg-primary");

      rerender(<Button variant="destructive">Destructive</Button>);
      button = screen.getByRole("button");
      expect(button).toHaveClass("bg-destructive");

      rerender(<Button variant="outline">Outline</Button>);
      button = screen.getByRole("button");
      expect(button).toHaveClass("border");
    });
  });

  describe("size prop", () => {
    it.each(["default", "sm", "lg", "icon", "icon-sm", "icon-lg"] as const)(
      "should render size: %s",
      (size) => {
        render(<Button size={size}>Test</Button>);
        const button = screen.getByRole("button");
        expect(button).toHaveAttribute("data-size", size);
      },
    );

    it("should apply size-specific CSS classes", () => {
      const { rerender } = render(<Button size="default">Default</Button>);
      let button = screen.getByRole("button");
      expect(button).toHaveClass("h-9");

      rerender(<Button size="sm">Small</Button>);
      button = screen.getByRole("button");
      expect(button).toHaveClass("h-8");

      rerender(<Button size="lg">Large</Button>);
      button = screen.getByRole("button");
      expect(button).toHaveClass("h-10");
    });

    it("should apply icon size classes correctly", () => {
      const { rerender } = render(<Button size="icon">Icon</Button>);
      let button = screen.getByRole("button");
      expect(button).toHaveClass("size-9");

      rerender(<Button size="icon-sm">Small Icon</Button>);
      button = screen.getByRole("button");
      expect(button).toHaveClass("size-8");

      rerender(<Button size="icon-lg">Large Icon</Button>);
      button = screen.getByRole("button");
      expect(button).toHaveClass("size-10");
    });
  });

  describe("asChild prop", () => {
    it("should render as anchor tag when asChild with Slot", () => {
      render(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>,
      );
      const link = screen.getByRole("link", { name: "Link Button" });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("data-slot", "button");
      expect(link).toHaveAttribute("href", "/test");
    });

    it("should not render button element when asChild is true", () => {
      render(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>,
      );
      const button = screen.queryByRole("button");
      expect(button).not.toBeInTheDocument();
    });
  });

  describe("interaction", () => {
    it("should handle click events", async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();
      render(<Button onClick={handleClick}>Click me</Button>);

      const button = screen.getByRole("button");
      await user.click(button);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("should be disabled when disabled prop is true", () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });

    it("should not call onClick when disabled", async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();
      render(
        <Button onClick={handleClick} disabled>
          Disabled
        </Button>,
      );

      const button = screen.getByRole("button");
      await user.click(button);

      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe("CSS classes", () => {
    it("should merge custom className with default classes", () => {
      render(<Button className="custom-class">Test</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("custom-class");
      expect(button).toHaveClass("inline-flex");
    });

    it("should include base classes for all buttons", () => {
      render(<Button>Test</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("inline-flex");
      expect(button).toHaveClass("items-center");
      expect(button).toHaveClass("justify-center");
    });

    it("should have disabled styling classes", () => {
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole("button");
      expect(button).toHaveClass("disabled:opacity-50");
      expect(button).toHaveClass("disabled:pointer-events-none");
    });
  });

  describe("additional props", () => {
    it("should pass through other HTML button attributes", () => {
      render(
        <Button type="submit" name="submit-btn" value="submit">
          Submit
        </Button>,
      );
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("type", "submit");
      expect(button).toHaveAttribute("name", "submit-btn");
      expect(button).toHaveAttribute("value", "submit");
    });

    it("should support aria attributes", () => {
      render(
        <Button aria-label="Close dialog" aria-describedby="dialog-desc">
          X
        </Button>,
      );
      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-label", "Close dialog");
      expect(button).toHaveAttribute("aria-describedby", "dialog-desc");
    });
  });
});
