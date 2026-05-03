"use client";

import * as ToastPrimitive from "@radix-ui/react-toast";
import { X } from "lucide-react";
import { createContext, useCallback, useContext, useState } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "success" | "error";

interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant: Variant;
}

interface ToastApi {
  show: (t: Omit<ToastItem, "id">) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const show = useCallback((t: Omit<ToastItem, "id">) => {
    const id = `t:${Math.random().toString(36).slice(2)}`;
    setItems((prev) => [...prev, { ...t, id }]);
  }, []);

  const api: ToastApi = {
    show,
    success: (title, description) => show({ title, description, variant: "success" }),
    error: (title, description) => show({ title, description, variant: "error" }),
  };

  return (
    <ToastContext.Provider value={api}>
      <ToastPrimitive.Provider duration={4000}>
        {children}
        {items.map((t) => (
          <ToastPrimitive.Root
            key={t.id}
            onOpenChange={(open) => {
              if (!open) setItems((prev) => prev.filter((p) => p.id !== t.id));
            }}
            className={cn(
              "rounded-md border p-3 shadow-lg",
              t.variant === "success" && "border-success bg-bg-elev",
              t.variant === "error" && "border-danger bg-bg-elev",
              t.variant === "default" && "border-border bg-bg-elev",
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <ToastPrimitive.Title className="text-sm font-semibold">
                  {t.title}
                </ToastPrimitive.Title>
                {t.description && (
                  <ToastPrimitive.Description className="text-sm text-fg-muted">
                    {t.description}
                  </ToastPrimitive.Description>
                )}
              </div>
              <ToastPrimitive.Close>
                <X className="size-4 text-fg-muted" />
              </ToastPrimitive.Close>
            </div>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed bottom-4 right-4 z-50 flex w-96 flex-col gap-2" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
