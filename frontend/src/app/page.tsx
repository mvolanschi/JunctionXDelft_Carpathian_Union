"use client";

import Orb from "@/components/Orb";

export default function HomePage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-black text-white">
      {/* Orb Background */}
      <div style={{ width: "100%", height: "600px", position: "relative" }}>
        <Orb
          hoverIntensity={0.5}
          rotateOnHover={true}
          hue={0}
          forceHoverState={false}
        />
      </div>

      {/* Foreground content */}
      <section className="text-center mt-10 z-10">
        <h1 className="text-4xl md:text-6xl font-bold">X-Guard</h1>
        <p className="text-lg md:text-xl mt-4 text-gray-300 max-w-2xl">
          Screen audio & video for extremist content responsibly
        </p>
      </section>
    </main>
  );
}
