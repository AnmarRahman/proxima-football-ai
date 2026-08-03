"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, BarChart3, Brain, Check, Database, ShieldCheck, Target } from "lucide-react";
import type { ElementType } from "react";
import { useEffect, useMemo, useState } from "react";

type AnalysisStep = {
  id: string;
  title: string;
  description: string;
  icon: ElementType;
};

type AIAnalysisLoaderProps = {
  playerName: string;
};

const STEP_DURATION_MS = 1250;
const STEP_HOLD_MS = 250;

function ProgressBar({ value, compact = false }: { value: number; compact?: boolean }) {
  return (
    <div className={`${compact ? "h-2" : "h-3"} relative w-full overflow-hidden rounded-full border border-white/15 bg-white/10`}>
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[#8f6b0d] via-[#d4af37] to-[#f6d66a] transition-[width] duration-100"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function AIAnalysisLoader({ playerName }: AIAnalysisLoaderProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);

  const steps = useMemo<AnalysisStep[]>(
    () => [
      {
        id: "record",
        title: "Loading league record",
        description: `Reading ${playerName}'s sourced domestic-league seasons.`,
        icon: Database,
      },
      {
        id: "model",
        title: "Verifying forecast record",
        description: "Checking the approved Tier A model version and release integrity.",
        icon: ShieldCheck,
      },
      {
        id: "history",
        title: "Reconstructing recent form",
        description: "Assembling age, experience, appearances, goals, trends, and season lags.",
        icon: BarChart3,
      },
      {
        id: "appearances",
        title: "Reviewing appearance estimate",
        description: "Pairing the stored appearance estimate with the player's historical progression.",
        icon: Activity,
      },
      {
        id: "goals",
        title: "Reviewing goal estimate",
        description: "Pairing the stored goal estimate with the player's historical progression.",
        icon: Target,
      },
      {
        id: "intervals",
        title: "Preparing uncertainty",
        description: "Applying the validated conditional interval policy where supported.",
        icon: Brain,
      },
    ],
    [playerName]
  );

  useEffect(() => {
    setCurrentStep(0);
    setStepProgress(0);
  }, [playerName]);

  useEffect(() => {
    if (currentStep >= steps.length) return;
    const tickMs = 50;
    const ticks = STEP_DURATION_MS / tickMs;
    let tick = 0;
    let holdTimer: number | undefined;
    const timer = window.setInterval(() => {
      tick += 1;
      setStepProgress(Math.min(100, (tick / ticks) * 100));
      if (tick >= ticks) {
        window.clearInterval(timer);
        setStepProgress(100);
        holdTimer = window.setTimeout(() => {
          setCurrentStep((value) => value + 1);
          setStepProgress(0);
        }, STEP_HOLD_MS);
      }
    }, tickMs);
    return () => {
      window.clearInterval(timer);
      if (holdTimer) window.clearTimeout(holdTimer);
    };
  }, [currentStep, steps.length]);

  const overallProgress = Math.min(
    100,
    ((currentStep + stepProgress / 100) / steps.length) * 100
  );
  const activeStep = steps[Math.min(currentStep, steps.length - 1)];

  return (
    <div className="animate-fade-in space-y-6 py-8" aria-live="polite" aria-busy="true">
      <div className="space-y-4 text-center">
        <div className="flex items-center justify-center gap-3">
          <div className="relative h-12 w-12">
            <div className="absolute inset-0 animate-spin rounded-full border-4 border-primary/25 border-t-primary" />
            <Brain className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 text-primary" />
          </div>
          <div className="text-left">
            <h2 className="text-2xl font-bold text-foreground">Preparing Forecast Report</h2>
            <p className="text-muted-foreground">Assembling {playerName}'s history and approved Tier A forecast.</p>
          </div>
        </div>
        <div className="mx-auto max-w-md space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Forecast preparation</span>
            <span className="font-medium text-primary">{Math.round(overallProgress)}%</span>
          </div>
          <ProgressBar value={overallProgress} />
        </div>
      </div>

      <Card className="border-primary/20 bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <activeStep.icon className="h-6 w-6 animate-pulse text-primary" />
            <span>{activeStep.title}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <p className="text-muted-foreground">{activeStep.description}</p>
            <ProgressBar value={stepProgress} compact />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {steps.map((step, index) => {
              const complete = index < currentStep;
              const active = index === currentStep;
              return (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 rounded-lg border p-3 transition-all duration-300 ${
                    active
                      ? "scale-[1.02] border-primary/60 bg-primary/15"
                      : complete
                        ? "border-emerald-500/30 bg-emerald-500/10"
                        : "border-border/40 bg-secondary/15 opacity-55"
                  }`}
                >
                  {complete ? (
                    <Check className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <step.icon className={`h-5 w-5 ${active ? "text-primary" : "text-muted-foreground"}`} />
                  )}
                  <span className={`text-sm font-medium ${complete ? "text-emerald-300" : active ? "text-primary" : "text-muted-foreground"}`}>
                    {step.title}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-3 gap-3 border-t border-border/40 pt-4 text-center">
            <div><p className="font-bold text-primary">Tier A</p><p className="text-xs text-muted-foreground">Approved model</p></div>
            <div><p className="font-bold text-primary">1 season</p><p className="text-xs text-muted-foreground">Forecast horizon</p></div>
            <div><p className="font-bold text-primary">2 outputs</p><p className="text-xs text-muted-foreground">Apps and goals</p></div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
