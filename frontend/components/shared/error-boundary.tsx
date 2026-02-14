"use client";

import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import { logError } from "@/lib/errors";
import { isDev } from "@/lib/env";
import { fallbackLng, languages } from "@/lib/i18n/settings";
import { useT } from "@/lib/i18n/client";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

// Extend ErrorInfo to include Next.js's digest property
interface NextJSErrorInfo extends React.ErrorInfo {
  digest?: string;
}

type DefaultErrorFallbackProps = {
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  onRetry: () => void;
  onGoHome: () => void;
  showDetails: boolean;
};

function DefaultErrorFallback({
  error,
  errorInfo,
  onRetry,
  onGoHome,
  showDetails,
}: DefaultErrorFallbackProps) {
  const { t } = useT("translation");

  return (
    <div className="flex min-h-[400px] items-center justify-center p-4">
      <div className="flex max-w-md flex-col items-center text-center">
        <div className="mb-4 rounded-full bg-destructive/10 p-4">
          <AlertTriangle className="h-12 w-12 text-destructive" />
        </div>

        <h2 className="mb-2 text-2xl font-semibold tracking-tight">
          {t("errors.boundary.title")}
        </h2>

        <p className="mb-6 text-sm text-muted-foreground">
          {error?.message || t("errors.boundary.description")}
        </p>

        {showDetails && error && (
          <details className="mb-6 w-full rounded-lg bg-muted p-4 text-left">
            <summary className="mb-2 cursor-pointer font-mono text-sm font-semibold">
              {t("errors.boundary.details")}
            </summary>
            <pre className="overflow-auto text-xs">
              <code>
                {error.toString()}
                {"\n"}
                {errorInfo?.componentStack}
              </code>
            </pre>
          </details>
        )}

        <div className="flex gap-3">
          <Button onClick={onRetry} variant="default">
            <RefreshCw className="mr-2 h-4 w-4" />
            {t("errors.boundary.tryAgain")}
          </Button>
          <Button onClick={onGoHome} variant="outline">
            <Home className="mr-2 h-4 w-4" />
            {t("errors.boundary.goHome")}
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Error Boundary Component
 *
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 *
 * @example
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error
    const nextJsInfo = errorInfo as NextJSErrorInfo;
    logError(error, {
      componentStack: errorInfo.componentStack,
      digest: nextJsInfo.digest,
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);

    // Update state with error info
    this.setState({
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = () => {
    const firstSegment = window.location.pathname.split("/")[1] || "";
    const lng = languages.includes(firstSegment) ? firstSegment : fallbackLng;
    window.location.href = `/${lng}/home`;
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <DefaultErrorFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleReset}
          onGoHome={this.handleGoHome}
          showDetails={isDev}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * Hook-based Error Boundary for functional components
 * Note: This is a wrapper around the class component for convenience
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">,
): React.ComponentType<P> {
  return function WrappedComponent(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}
