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
      <VoiceBars keyword="fuck" />

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
                {/* Step 1: The Challenge — unchanged */}
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

                {/* Step 2: Moderation System */}
                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    The Moderation System
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    Once audio is uploaded, X-Guard begins its{" "}
                    <span className="text-white font-semibold">
                      moderation pipeline
                    </span>
                    . Using{" "}
                    <span className="text-white font-semibold">
                      Whisper transcription
                    </span>{" "}
                    and{" "}
                    <span className="text-white font-semibold">
                      PyAnnote speaker diarization
                    </span>
                    , the system understands what was said, when, and by whom.
                    Then, a{" "}
                    <span className="text-white font-semibold">
                      large language model classifier
                    </span>{" "}
                    analyzes each sentence — detecting profanity, hate speech,
                    or extremist language and marking exact problem spans with
                    detailed rationales. Confidence thresholds ensure only
                    reliable segments are flagged.
                  </p>
                </Step>

                {/* Step 3: Negative Output Handling */}
                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    Rewriting & Regeneration
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    Once problematic speech is found, X-Guard’s{" "}
                    <span className="text-white font-semibold">
                      negative output handling system
                    </span>{" "}
                    takes over. Offensive or biased content is{" "}
                    <span className="text-white font-semibold">
                      rewritten ethically
                    </span>{" "}
                    — preserving meaning but removing harm. A dictionary handles
                    common profanity instantly, while{" "}
                    <span className="text-white font-semibold">
                      LLaMA-based
                    </span>{" "}
                    rewriting adapts complex phrases professionally. The system
                    then clones each speaker’s voice to{" "}
                    <span className="text-white font-semibold">
                      regenerate clean audio
                    </span>{" "}
                    using neural speech synthesis that matches the original tone
                    and pacing.
                  </p>
                </Step>

                {/* Step 4: Why It Matters (with quote) */}
                <Step>
                  <h2
                    className="text-3xl font-semibold mb-3"
                    style={{ color: accentColor }}
                  >
                    Why It Matters
                  </h2>
                  <p className="text-gray-300 leading-relaxed text-lg">
                    X-Guard combines responsible AI, advanced voice cloning, and
                    linguistic analysis to ensure that speech datasets remain
                    useful without spreading harm. It helps institutions and
                    creators maintain ethical standards while preserving the
                    authenticity of human expression.
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
