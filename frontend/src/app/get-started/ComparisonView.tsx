"use client";

import ElectricBorder from "@/components/ElectricBorder";
import { ArrowRight } from "lucide-react";

export default function ComparisonView() {
  const accentColor = "#4cc9f0";

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-8 py-20">
      <h1 className="text-4xl md:text-5xl font-bold mb-16 text-center drop-shadow-[0_0_25px_rgba(255,255,255,0.8)]">
        Ethical Transformation Comparison
      </h1>

      <div className="flex flex-col md:flex-row items-center justify-center gap-12 w-full max-w-6xl">
        {/* LEFT: Flagged */}
        <ElectricBorder color={accentColor} speed={3} chaos={2}>
          <div className="bg-black/80 border border-white/10 rounded-3xl p-8 md:p-10 w-[330px] md:w-[400px] space-y-6">
            <h2 className="text-2xl font-semibold text-red-400">
              Flagged (Problematic Language)
            </h2>
            <p className="leading-relaxed text-lg text-red-500">
              scheduling this stuff can be{" "}
              <span className="font-semibold">fucking annoying</span> when
              volunteers cancel last minute.
            </p>
            <p className="leading-relaxed text-lg text-red-500 font-semibold">
              I hate those damn Romanians, taking our jobs and all.
            </p>
            <p className="leading-relaxed text-lg text-red-500 font-semibold">
              All they do is lay on the couch and take benefits.
            </p>
          </div>
        </ElectricBorder>

        {/* ARROW */}
        <div className="flex justify-center items-center">
          <ArrowRight
            size={80}
            className="text-white drop-shadow-[0_0_20px_rgba(76,201,240,0.8)] animate-pulse"
          />
        </div>

        {/* RIGHT: Refined */}
        <ElectricBorder color={accentColor} speed={3} chaos={2}>
          <div className="bg-black/80 border border-white/10 rounded-3xl p-8 md:p-10 w-[330px] md:w-[400px] space-y-6">
            <h2 className="text-2xl font-semibold text-green-400">
              Refined (Ethically Balanced)
            </h2>
            <p className="leading-relaxed text-lg text-green-400">
              scheduling this stuff can be{" "}
              <span className="font-semibold">really annoying</span> when
              volunteers cancel last minute.
            </p>
            <p className="leading-relaxed text-lg text-green-400 font-semibold">
              I’ve been upset lately about job insecurity and competition, but I
              know blaming people isn’t right.
            </p>
            <p className="leading-relaxed text-lg text-green-400 font-semibold">
              Some people rely on benefits when times are tough, and I should
              try to be more understanding.
            </p>
          </div>
        </ElectricBorder>
      </div>
    </main>
  );
}
