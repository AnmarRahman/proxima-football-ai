"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Activity, BarChart3, Brain, Target, TrendingUp, Zap } from "lucide-react";
import { useEffect, useState } from "react";

interface AnalysisStep {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  duration: number;
}

interface AIAnalysisLoaderProps {
  playerName: string;
  onComplete: () => void;
}

// Helper: combine base and indicator colors using custom classes on the wrapper
const YellowProgress = ({ value, className = "" }: { value: number; className?: string }) => {
  return (
    <div className={`relative w-full h-3 rounded-md overflow-hidden bg-white/25 border border-white/20 ${className}`}>
      <div
        className="absolute inset-y-0 left-0 bg-yellow-500"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
};

const YellowStepProgress = ({ value, className = "" }: { value: number; className?: string }) => {
  return (
    <div className={`relative w-full h-2 rounded-md overflow-hidden bg-white/25 border border-white/15 ${className}`}>
      <div
        className="absolute inset-y-0 left-0 bg-yellow-500"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
};

export function AIAnalysisLoader({ playerName, onComplete }: AIAnalysisLoaderProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);

  const analysisSteps: AnalysisStep[] = [
    { id: "goals", title: "Adding up goals", description: `Analyzing ${playerName}'s scoring patterns across 247 matches...`, icon: Target, duration: 2000 },
    { id: "injuries", title: "Checking injury record", description: "Evaluating injury history and physical durability factors...", icon: Activity, duration: 1800 },
    { id: "personality", title: "Analyzing player personality", description: "Processing leadership qualities, mentality, and career ambitions...", icon: Brain, duration: 2200 },
    { id: "performance", title: "Studying performance trends", description: "Examining seasonal patterns, peak periods, and consistency metrics...", icon: TrendingUp, duration: 2000 },
    { id: "stats", title: "Crunching advanced stats", description: "Processing xG, xA, defensive actions, and tactical contributions...", icon: BarChart3, duration: 1900 },
    { id: "prediction", title: "Generating AI predictions", description: "Combining 2.3M data points to predict career trajectory...", icon: Zap, duration: 2100 },
  ];

  useEffect(() => {
    if (currentStep >= analysisSteps.length) {
      const t = setTimeout(() => onComplete(), 800);
      return () => clearTimeout(t);
    }

    const step = analysisSteps[currentStep];
    const interval = 50;
    const totalSteps = step.duration / interval;
    let stepCounter = 0;

    const timer = setInterval(() => {
      stepCounter++;
      const currentStepProgress = (stepCounter / totalSteps) * 100;
      const overallProgress = ((currentStep + stepCounter / totalSteps) / analysisSteps.length) * 100;
      setStepProgress(Math.min(currentStepProgress, 100));
      setProgress(Math.min(overallProgress, 100));

      if (stepCounter >= totalSteps) {
        clearInterval(timer);
        setCurrentStep((prev) => prev + 1);
        setStepProgress(0);
      }
    }, interval);

    return () => clearInterval(timer);
  }, [currentStep, analysisSteps.length, onComplete]);

  const currentStepData = analysisSteps[currentStep];
  const isComplete = currentStep >= analysisSteps.length;

  return (
    <div className="space-y-6 py-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center space-x-3">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
            <Brain className="w-6 h-6 text-primary absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">AI Analysis in Progress</h2>
            <p className="text-muted-foreground">Predicting {playerName}'s career trajectory...</p>
          </div>
        </div>

        {/* Overall Progress (white track, yellow fill) */}
        <div className="max-w-md mx-auto space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="text-primary font-medium">{Math.round(progress)}%</span>
          </div>
          <YellowProgress value={progress} />
        </div>
      </div>

      {/* Analysis Steps */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center space-x-3">
            {currentStepData && (
              <>
                <currentStepData.icon className="w-6 h-6 text-primary animate-pulse" />
                <span>{currentStepData.title}</span>
              </>
            )}
            {isComplete && (
              <>
                <Zap className="w-6 h-6 text-green-500" />
                <span className="text-green-500">Analysis Complete!</span>
              </>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Step Description */}
          {currentStepData && (
            <div className="space-y-3">
              <p className="text-muted-foreground">{currentStepData.description}</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Step Progress</span>
                  <span className="text-primary font-medium">{Math.round(stepProgress)}%</span>
                </div>
                <YellowStepProgress value={stepProgress} />
              </div>
            </div>
          )}

          {/* Steps List */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {analysisSteps.map((step, index) => {
              const isCurrentStep = index === currentStep;
              const isCompletedStep = index < currentStep;

              return (
                <div
                  key={step.id}
                  className={`flex items-center space-x-3 p-3 rounded-lg transition-all duration-500 ${
                    isCurrentStep
                      ? "bg-primary/20 border-2 border-primary/50 shadow-lg scale-105"
                      : isCompletedStep
                      ? "bg-green-500/10 border border-green-500/30"
                      : "bg-secondary/20 border border-border/30 opacity-60"
                  }`}
                >
                  <div className="relative">
                    <step.icon
                      className={`w-5 h-5 ${
                        isCurrentStep
                          ? "text-primary animate-pulse"
                          : isCompletedStep
                          ? "text-green-500"
                          : "text-muted-foreground"
                      }`}
                    />
                    {isCompletedStep && (
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full flex items-center justify-center">
                        <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-medium truncate ${
                      isCurrentStep
                        ? "text-primary"
                        : isCompletedStep
                        ? "text-green-500"
                        : "text-muted-foreground"
                    }`}>
                      {step.title}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Fun Stats */}
          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border/30">
            <div className="text-center">
              <div className="text-lg font-bold text-primary animate-pulse">
                {Math.floor(Math.random() * 1000) + 1500}
              </div>
              <div className="text-xs text-muted-foreground">Data Points/sec</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-yellow-500 animate-pulse">
                {Math.floor(Math.random() * 50) + 200}
              </div>
              <div className="text-xs text-muted-foreground">Matches Analyzed</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-green-500 animate-pulse">
                {Math.floor(Math.random() * 10) + 85}%
              </div>
              <div className="text-xs text-muted-foreground">Accuracy Score</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
