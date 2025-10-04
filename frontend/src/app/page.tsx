"use client";

import Orb from "@/components/Orb";
import VoiceBars from "@/components/VoiceBars";
import { Button } from "@/components/ui/button"; // shadcn/ui if you have it — otherwise use normal <button>

export default function HomePage() {
  return (
    <main className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white overflow-hidden">
      {/* Voice Bars behind */}
      <VoiceBars keyword="laptop" />

      {/* Orb with content inside */}
      <div
        className="relative flex items-center justify-center"
        style={{
          width: "100%",
          height: "600px",
          zIndex: 1,
        }}
      >
        {/* Orb Background */}
        <Orb
          hoverIntensity={0.5}
          rotateOnHover={true}
          hue={0}
          forceHoverState={false}
        />

        {/* Foreground text & buttons */}
        <div className="absolute text-center select-none pointer-events-none flex flex-col items-center">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight drop-shadow-[0_0_25px_rgba(255,255,255,0.5)] mb-4">
            X-Guard
          </h1>
          <p className="text-base md:text-lg text-gray-300 max-w-md mb-8 drop-shadow-[0_0_15px_rgba(255,255,255,0.25)]">
            Screen audio & video for xtremist content responsibly
          </p>

          <div className="flex gap-4 pointer-events-auto">
            <button className="px-6 py-3 bg-white text-black font-semibold rounded-full shadow-lg hover:bg-gray-200 transition">
              Get Started
            </button>
            <button className="px-6 py-3 border border-white/40 text-white font-semibold rounded-full hover:bg-white/10 transition">
              Learn More
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
