"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface ScoreBreakdownLine {
  /** Stable key — e.g. ``backup_gap`` or ``jjscan_high``. */
  key: string;
  /** Magnitude of the deduction (positive integer). */
  amount: number;
  /** Whether an auto-fix is available for the underlying signal. */
  autoFixable?: boolean;
  /** Optional human label — falls back to a derived one. */
  label?: string;
}

export interface ConfidenceGaugeProps {
  score: number;
  base?: number;
  /** Penalty rows that brought the score below ``base``. */
  deductions: ScoreBreakdownLine[];
  /** Bonus rows applied after penalties. */
  boosts?: ScoreBreakdownLine[];
  /** Called when the user clicks "Fix" on an auto-fixable deduction. */
  onApplyAutoFix?: (key: string) => void;
  /** Called when the user clicks "Override score". */
  onOverride?: () => void;
  /** Subject identifier used for the audit-history link (e.g. JCL name). */
  subjectName?: string;
}

type Zone = "red" | "amber" | "green";

function zoneFor(score: number): Zone {
  if (score < 60) return "red";
  if (score < 80) return "amber";
  return "green";
}

const ZONE_LABEL: Record<Zone, string> = {
  red: "Red — blocked",
  amber: "Amber — reviewer approval needed",
  green: "Green — clear to promote",
};

const ZONE_TEXT_CLASS: Record<Zone, string> = {
  red: "text-danger",
  amber: "text-warning",
  green: "text-success",
};

/** Hex along the red→amber→green gradient. Pure clamped linear interpolation
 * between three stops so 62→94→100 animates as a smooth sweep. */
type ColorStop = { at: number; rgb: readonly [number, number, number] };

const COLOR_STOPS: readonly ColorStop[] = [
  { at: 0, rgb: [220, 38, 38] }, // red-600
  { at: 60, rgb: [217, 119, 6] }, // amber-600
  { at: 80, rgb: [16, 185, 129] }, // emerald-500
  { at: 100, rgb: [5, 150, 105] }, // emerald-600
] as const;

function colorFor(score: number): string {
  const clamped = Math.max(0, Math.min(100, score));
  let lower: ColorStop = COLOR_STOPS[0]!;
  let upper: ColorStop = COLOR_STOPS[COLOR_STOPS.length - 1]!;
  for (let i = 0; i < COLOR_STOPS.length - 1; i++) {
    const a = COLOR_STOPS[i]!;
    const b = COLOR_STOPS[i + 1]!;
    if (clamped >= a.at && clamped <= b.at) {
      lower = a;
      upper = b;
      break;
    }
  }
  const span = upper.at - lower.at || 1;
  const t = (clamped - lower.at) / span;
  const lerp = (a: number, b: number) => Math.round(a + (b - a) * t);
  const r = lerp(lower.rgb[0], upper.rgb[0]);
  const g = lerp(lower.rgb[1], upper.rgb[1]);
  const b = lerp(lower.rgb[2], upper.rgb[2]);
  return `rgb(${r}, ${g}, ${b})`;
}

const HUMAN_LABELS: Record<string, string> = {
  backup_gap: "Backup gap",
  region_mismatch: "Region mismatch",
  historical_abends: "Historical ABENDs (30d)",
  jjscan_critical: "Critical JJSCAN+ findings",
  jjscan_high: "High JJSCAN+ findings",
  jjscan_medium: "Medium JJSCAN+ findings",
  jjscan_low: "Low JJSCAN+ findings",
  jjscan_info: "Info JJSCAN+ findings",
  spec_match_bonus: "Spec match bonus",
  soft_rounding: "Soft rounding",
};

function labelFor(line: ScoreBreakdownLine): string {
  if (line.label) return line.label;
  return HUMAN_LABELS[line.key] ?? line.key;
}

/** Animated number tween for the centre score. Pure JS so we don't need
 * framer-motion just for this one transition. */
function useAnimatedNumber(target: number, durationMs = 400): number {
  const [value, setValue] = useState(target);
  useEffect(() => {
    let raf: number;
    const start = performance.now();
    const from = value;
    const delta = target - from;
    if (delta === 0) return;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      // ease-out cubic.
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(from + delta * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // We intentionally omit `value` from deps — re-running on every value
    // tick would create a feedback loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, durationMs]);
  return value;
}

export function ConfidenceGauge({
  score,
  base = 100,
  deductions,
  boosts = [],
  onApplyAutoFix,
  onOverride,
  subjectName,
}: ConfidenceGaugeProps) {
  const zone = zoneFor(score);
  const color = colorFor(score);
  const animated = useAnimatedNumber(score);

  const top3 = [...deductions]
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 3);

  // SVG arc: 270° sweep starting at -135°, ending at +135° (six o'clock open).
  const radius = 80;
  const stroke = 18;
  const cx = 110;
  const cy = 110;
  const totalSweep = 270;
  const startAngle = -225; // start at 7 o'clock
  const endAngle = startAngle + totalSweep;
  const valueAngle = startAngle + (totalSweep * Math.max(0, Math.min(100, score))) / 100;

  return (
    <Card data-testid="confidence-gauge">
      <CardContent className="flex flex-col items-center pt-6">
        <svg
          viewBox="0 0 220 220"
          className="h-56 w-56"
          aria-label={`Confidence score ${score} of ${base}`}
          role="img"
        >
          {/* track */}
          <path
            d={describeArc(cx, cy, radius, startAngle, endAngle)}
            fill="none"
            stroke="rgb(var(--color-bg-subtle, 230 232 237))"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          {/* value arc — colour transitions smoothly with score */}
          <path
            d={describeArc(cx, cy, radius, startAngle, valueAngle)}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            style={{
              transition:
                "stroke 600ms cubic-bezier(0.22, 1, 0.36, 1), d 600ms",
            }}
          />
          <text
            x={cx}
            y={cy + 4}
            textAnchor="middle"
            className="select-none font-bold"
            style={{ fontSize: "44px", fill: color, transition: "fill 600ms" }}
          >
            {animated}
          </text>
          <text
            x={cx}
            y={cy + 36}
            textAnchor="middle"
            className="select-none fill-fg-muted"
            style={{ fontSize: "12px" }}
          >
            of {base}
          </text>
        </svg>

        <div
          className={cn("mt-2 text-sm font-semibold", ZONE_TEXT_CLASS[zone])}
          data-testid="confidence-zone"
        >
          {ZONE_LABEL[zone]}
        </div>

        {top3.length > 0 && (
          <div className="mt-6 w-full">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fg-muted">
              Top {top3.length} reasons
            </h3>
            <ul className="space-y-2">
              {top3.map((line) => (
                <li
                  key={line.key}
                  className="flex items-center justify-between rounded-md border border-border bg-bg-elev px-3 py-2 text-sm"
                  data-testid={`reason-${line.key}`}
                >
                  <div>
                    <div className="font-medium">{labelFor(line)}</div>
                    <div className="text-xs text-fg-muted">−{line.amount}</div>
                  </div>
                  {line.autoFixable && onApplyAutoFix && (
                    <Button
                      size="sm"
                      onClick={() => onApplyAutoFix(line.key)}
                      data-testid={`fix-${line.key}`}
                    >
                      Fix
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {boosts.length > 0 && (
          <ul className="mt-4 w-full space-y-1 text-xs text-fg-muted">
            {boosts.map((b) => (
              <li
                key={b.key}
                className="flex items-center justify-between"
                data-testid={`boost-${b.key}`}
              >
                <span>{labelFor(b)}</span>
                <span>+{b.amount}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-6 flex w-full items-center justify-between gap-3 text-xs">
          {onOverride ? (
            <button
              type="button"
              onClick={onOverride}
              className="text-fg-muted underline-offset-4 hover:text-fg hover:underline"
            >
              Override score
            </button>
          ) : (
            <span />
          )}
          {subjectName && (
            <a
              href={`/audit?subject=${encodeURIComponent(subjectName)}`}
              className="text-fg-muted underline-offset-4 hover:text-fg hover:underline"
            >
              Audit history
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// --- SVG arc math --------------------------------------------------------

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
) {
  const start = polar(cx, cy, r, endAngle);
  const end = polar(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
  return [
    "M",
    start.x,
    start.y,
    "A",
    r,
    r,
    0,
    largeArc,
    0,
    end.x,
    end.y,
  ].join(" ");
}
