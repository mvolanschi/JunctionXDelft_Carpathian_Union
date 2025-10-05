"use client";

import ElectricBorder from "@/components/ElectricBorder";
import { motion } from "framer-motion";

export default function FlaggedView() {
  const accentColor = "#4cc9f0";

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-8 py-20 relative overflow-hidden">
      {/* Glow pulse background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(76,201,240,0.08)_0%,transparent_70%)]" />

      <h1 className="text-4xl md:text-5xl font-bold mb-16 text-center drop-shadow-[0_0_25px_rgba(255,255,255,0.8)]">
        Flagged Transcript
      </h1>

      <ElectricBorder color={accentColor} speed={3} chaos={2}>
        <div className="bg-black/80 border border-white/10 rounded-3xl p-10 w-[360px] md:w-[480px] space-y-6 text-left">
          <h2 className="text-2xl font-semibold text-red-400 mb-4">
            Problematic Segments
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

          {/* Divider */}
          <div className="border-t border-white/10 my-6" />

          {/* Loading pulse */}
          <div className="flex flex-col items-center space-y-4">
            <motion.div
              className="w-10 h-10 rounded-full"
              style={{
                background:
                  "radial-gradient(circle, #4cc9f0 0%, #4361ee 40%, transparent 70%)",
              }}
              animate={{
                scale: [1, 1.3, 1],
                opacity: [0.8, 1, 0.8],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            <p className="text-white/70 font-semibold tracking-wide text-sm uppercase">
              Analyzing content...
            </p>
          </div>
        </div>
      </ElectricBorder>
    </main>
  );
}
