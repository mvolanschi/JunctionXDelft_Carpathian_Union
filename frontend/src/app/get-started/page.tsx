"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import Orb from "@/components/Orb";
import VoiceBars from "@/components/VoiceBars";
import ElectricBorder from "@/components/ElectricBorder";

export default function GetStartedPage() {
  const accentColor = "#4cc9f0";
  const [file, setFile] = useState<File | null>(null);
  const [modifiedAudio, setModifiedAudio] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [cleanTranscript, setCleanTranscript] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTransforming, setIsTransforming] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(1); // 1: Upload, 2: Transcript, 3: Refined, 4: Audio

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setModifiedAudio(null);
      setTranscript(null);
      setCleanTranscript(null);
      setCurrentStep(1);
    }
  };

  const handleProcess = () => {
    if (!file) return;
    setIsProcessing(true);

    // Simulate backend: transcription with highlighted "bad" words
    setTimeout(() => {
      setTranscript(
        "We should avoid using hateful or extreme speech in datasets. Some people might use words like <span class='text-red-500 font-semibold'>idiot</span> or <span class='text-red-500 font-semibold'>hate</span>, and our system flags them for review."
      );
      setIsProcessing(false);
      setCurrentStep(2);
    }, 2000);
  };

  const handleTransform = () => {
    setIsTransforming(true);

    // Simulate cleaned version and modified audio
    setTimeout(() => {
      setCleanTranscript(
        "We should avoid using hateful or extreme speech in datasets. Some people might use words like <span class='text-green-400 font-semibold'>individual</span> or <span class='text-green-400 font-semibold'>dislike</span>, and our system refines them for balance."
      );
      setIsTransforming(false);
      setCurrentStep(3);
    }, 2000);
  };

  const handleGenerateAudio = () => {
    setIsProcessing(true);
    setTimeout(() => {
      if (file) setModifiedAudio(URL.createObjectURL(file));
      setIsProcessing(false);
      setCurrentStep(4);
    }, 2000);
  };

  const handleStartOver = () => {
    setFile(null);
    setTranscript(null);
    setCleanTranscript(null);
    setModifiedAudio(null);
    setCurrentStep(1);
  };

  return (
    <main className="relative flex flex-col items-center justify-center min-h-screen bg-black text-white overflow-hidden">
      <VoiceBars keyword="upload" />
      <Orb hoverIntensity={0.5} rotateOnHover hue={0} forceHoverState={false} />

      <div className="relative z-10 flex flex-col items-center text-center space-y-8 px-6 w-full max-w-4xl">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.8)]">
          Upload & Transform
        </h1>
        <p className="text-lg md:text-xl font-semibold text-white drop-shadow-[0_0_20px_rgba(255,255,255,0.5)] max-w-2xl">
          Upload your audio file — we'll analyze, flag, and ethically transform
          its content.
        </p>

        <ElectricBorder color={accentColor} speed={3} chaos={2}>
          <div className="bg-black/80 rounded-3xl p-10 w-full flex flex-col items-center justify-center space-y-6">
            <AnimatePresence mode="wait">
              {/* Step 1: Upload */}
              {currentStep === 1 && (
                <div
                  key="upload"
                  className="w-full flex flex-col items-center space-y-6"
                >
                  {!file ? (
                    <label
                      htmlFor="audio-upload"
                      className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-white/40 rounded-2xl cursor-pointer hover:bg-white/10 transition"
                    >
                      <p className="text-white/70 mb-2 text-lg">
                        Click or drag to upload
                      </p>
                      <p className="text-sm text-gray-400">
                        Accepted formats: .mp3, .wav
                      </p>
                      <input
                        id="audio-upload"
                        type="file"
                        accept="audio/*"
                        className="hidden"
                        onChange={handleFileChange}
                      />
                    </label>
                  ) : (
                    <>
                      <p className="text-white/80">{file.name}</p>
                      <Button
                        onClick={handleProcess}
                        disabled={isProcessing}
                        className="px-8 py-3 bg-white text-black font-semibold rounded-full shadow-lg hover:bg-gray-200 transition"
                      >
                        {isProcessing ? "Processing..." : "Process Audio"}
                      </Button>
                    </>
                  )}
                </div>
              )}

              {/* Step 2: Original Transcript */}
              {currentStep === 2 && transcript && (
                <div
                  key="transcript"
                  className="w-full flex flex-col items-center space-y-6"
                >
                  <div className="w-full text-left space-y-4">
                    <h3
                      className="text-2xl font-semibold"
                      style={{ color: accentColor }}
                    >
                      Transcript
                    </h3>
                    <div
                      className="bg-white/5 border border-white/10 rounded-xl p-4 text-left leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: transcript }}
                    />
                    {file && (
                      <div className="mt-4">
                        <audio
                          controls
                          src={URL.createObjectURL(file)}
                          className="w-full rounded-lg shadow-lg"
                        />
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={handleTransform}
                    disabled={isTransforming}
                    className="px-8 py-3 bg-white text-black font-semibold rounded-full shadow-lg hover:bg-gray-200 transition"
                  >
                    {isTransforming
                      ? "Transforming..."
                      : "Transform Transcript"}
                  </Button>
                </div>
              )}

              {/* Step 3: Refined Transcript */}
              {currentStep === 3 && cleanTranscript && (
                <div
                  key="refined"
                  className="w-full flex flex-col items-center space-y-6"
                >
                  <div className="w-full text-left space-y-4">
                    <h3
                      className="text-2xl font-semibold"
                      style={{ color: accentColor }}
                    >
                      Refined Transcript
                    </h3>
                    <div
                      className="bg-white/5 border border-white/10 rounded-xl p-4 text-left leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: cleanTranscript }}
                    />
                  </div>
                  <Button
                    onClick={handleGenerateAudio}
                    disabled={isProcessing}
                    className="px-8 py-3 bg-white text-black font-semibold rounded-full shadow-lg hover:bg-gray-200 transition"
                  >
                    {isProcessing
                      ? "Generating Audio..."
                      : "Generate Modified Audio"}
                  </Button>
                </div>
              )}

              {/* Step 4: Modified Audio */}
              {currentStep === 4 && modifiedAudio && (
                <div
                  key="audio"
                  className="w-full flex flex-col items-center space-y-6"
                >
                  <div className="w-full space-y-6">
                    <h3
                      className="text-3xl font-semibold"
                      style={{ color: accentColor }}
                    >
                      Modified Audio
                    </h3>
                    <div className="bg-white/5 border border-white/10 rounded-xl p-8">
                      <audio
                        controls
                        src={modifiedAudio}
                        className="w-full rounded-lg shadow-lg mb-6"
                      />
                      <div className="flex gap-4 justify-center">
                        <a
                          href={modifiedAudio}
                          download="modified_audio.wav"
                          className="inline-block px-8 py-3 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition shadow-lg"
                        >
                          Download
                        </a>
                        <button
                          onClick={handleStartOver}
                          className="px-8 py-3 bg-white/10 text-white font-semibold rounded-full hover:bg-white/20 transition border border-white/30 shadow-lg"
                        >
                          Start Over
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </AnimatePresence>
          </div>
        </ElectricBorder>
      </div>
    </main>
  );
}
