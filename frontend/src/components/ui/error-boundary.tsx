"use client";

import { Component, ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./card";

interface State {
  err: Error | null;
}

interface Props {
  children: ReactNode;
  fallback?: (err: Error, reset: () => void) => ReactNode;
}

export class ErrorBoundary extends Component<Props, State> {
  override state: State = { err: null };

  static getDerivedStateFromError(err: Error): State {
    return { err };
  }

  override componentDidCatch(err: Error) {
    if (typeof console !== "undefined") {
      console.error("[helios] error boundary caught", err);
    }
  }

  reset = () => this.setState({ err: null });

  override render() {
    if (this.state.err) {
      if (this.props.fallback) return this.props.fallback(this.state.err, this.reset);
      return (
        <Card>
          <CardHeader>
            <CardTitle>Something broke.</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-2 text-sm text-fg-muted">{this.state.err.message}</p>
            <button
              type="button"
              onClick={this.reset}
              className="text-sm text-accent underline-offset-2 hover:underline"
            >
              try again
            </button>
          </CardContent>
        </Card>
      );
    }
    return this.props.children;
  }
}
