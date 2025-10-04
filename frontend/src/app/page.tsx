"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";

import Orb from "@/components/Orb";
import VoiceBars from "@/components/VoiceBars";
import { Button } from "@/components/ui/button";
import Stepper, { Step } from "@/components/Stepper";
import ElectricBorder from "@/components/ElectricBorder";

export default function HomePage() {
  const [showStepper, setShowStepper] = useState(false);
  const router = useRouter();

  const accentColor = "#4cc9f0";

  const handleComplete = () => {
    setTimeout(() => router.push("/get-started"), 1000);
  };

  return (
    <main className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white overflow-hidden">
      <VoiceBars keyword="laptop" />

      <div
        className="relative flex items-center justify-center"
        style={{ width: "100%", height: "600px", zIndex: 1 }}
      >
        <Orb
          hoverIntensity={0.5}
          rotateOnHover
          hue={0}
          forceHoverState={false}
        />

        <div className="absolute flex flex-col items-center text-center select-none pointer-events-none">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.8)] mb-4">
            X-Guard
          </h1>

          <p className="text-base md:text-lg font-semibold text-white max-w-md mb-8 drop-shadow-[0_0_20px_rgba(255,255,255,0.5)]">
            Filtering extremism. Amplifying inclusion.
          </p>

          <div className="flex gap-4 pointer-events-auto">
            <Link href="/get-started">
              <Button className="px-6 py-3 bg-white text-black font-semibold rounded-full shadow-lg hover:bg-gray-200 transition">
                Get Started
              </Button>
            </Link>

            <Button
              onClick={() => setShowStepper(true)}
              className="px-6 py-3 border border-white/40 text-white font-semibold rounded-full hover:bg-white/10 transition"
            >
              Learn More
            </Button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showStepper && (
          <motion.div
            className="fixed inset-0 bg-black flex items-center justify-center z-50 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="relative w-full max-w-xl">
              <button
                onClick={() => setShowStepper(false)}
                className="absolute -top-13 right-5 md:-top-12 md:right-6 text-2xl md:text-3xl font-light z-10 transition-transform hover:scale-125"
                style={{
                  lineHeight: 1,
                  color: "#4cc9f0",
                  textShadow:
                    "0 0 8px rgba(76,201,240,0.8), 0 0 15px rgba(76,201,240,0.6), 0 0 25px rgba(76,201,240,0.4)",
                }}
              >
                ×
              </button>

              <Stepper
                onFinalStepCompleted={handleComplete}
                nextButtonText="Next"
                backButtonText="Back"
              >
                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    The Challenge
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    Speech and voice data are vital for developing inclusive AI,
                    but they can contain extremist views or biased content. TU
                    Delft's{" "}
                    <span className="text-white font-semibold">
                      Extreme Challenge
                    </span>{" "}
                    tasks innovators with designing systems that responsibly
                    detect and flag such content — ensuring safe, inclusive AI
                    training data.
                  </p>
                </Step>

                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    Enter X-Guard
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    <span className="text-white font-semibold">X-Guard</span> is
                    our answer — a smart screening platform that listens,
                    learns, and identifies extremist or harmful speech in real
                    time. It's not just a detector; it's a responsible filter
                    built on ethical AI, designed to preserve open data while
                    eliminating toxic bias.
                  </p>
                </Step>

                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    How It Works
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    Using speech-to-text, semantic embeddings, and tone
                    modeling, X-Guard highlights extremist language, assigns a
                    confidence score, and provides precise{" "}
                    <span className="text-white font-semibold">timestamps</span>{" "}
                    in large datasets — helping researchers and developers clean
                    their data efficiently and transparently.
                  </p>
                </Step>

                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    Why It Matters
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    X-Guard empowers institutions and creators to build fair,
                    inclusive, and safe speech technology. By responsibly
                    defining what constitutes "extreme" or "bad" speech, we're
                    ensuring AI reflects humanity's diversity — not its
                    division.
                  </p>
                  <p className="text-gray-400 italic mt-4">
                    "Responsible data is the foundation of responsible AI."
                  </p>
                </Step>
              </Stepper>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
