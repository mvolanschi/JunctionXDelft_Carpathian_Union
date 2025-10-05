"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import Orb from "@/components/Orb";
import VoiceBars from "@/components/VoiceBars";
import ElectricBorder from "@/components/ElectricBorder";

export default function GetStartedPage() {
  const accentColor = "#4cc9f0";
  const [file, setFile] = useState<File | null>(null);
  const [modifiedAudios, setModifiedAudios] = useState<string[]>([]);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [cleanTranscript, setCleanTranscript] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTransforming, setIsTransforming] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(1);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setModifiedAudios([]);
      setTranscript(null);
      setCleanTranscript(null);
      setCurrentStep(1);
    }
  };

  const handleProcess = async () => {
    if (!file) return;
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/moderations`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Build transcript with flagged content highlighted in red
      let originalTranscript = '';
      const flaggedLabels = ['PROFANITY', 'HATE', 'EXTREMIST', 'BOTH'];

      for (const segment of data.segments) {
        const text = segment.text;
        const classification = segment.classification;

        if (flaggedLabels.includes(classification.label) && classification.spans.length > 0) {
          // Highlight flagged spans in red
          let highlightedText = text;
          const sortedSpans = [...classification.spans].sort((a, b) => b.char_start - a.char_start);

          for (const span of sortedSpans) {
            const before = highlightedText.substring(0, span.char_start);
            const flagged = highlightedText.substring(span.char_start, span.char_end);
            const after = highlightedText.substring(span.char_end);
            highlightedText = `${before}<span class='text-red-500 font-semibold'>${flagged}</span>${after}`;
          }
          originalTranscript += highlightedText + ' ';
        } else {
          originalTranscript += text + ' ';
        }
      }

      setTranscript(originalTranscript);
      setIsProcessing(false);
      setCurrentStep(2);
    } catch (error) {
      console.error('Error processing audio:', error);
      setIsProcessing(false);
      alert('Failed to process audio. Make sure the backend server is running.');
    }
  };

  const handleTransform = async () => {
    setIsTransforming(true);

    try {
      const formData = new FormData();
      formData.append('file', file!);
      formData.append('mode', 'negative_output_handling');

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/moderations`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Build cleaned transcript with replacements highlighted in green
      let cleanedTranscript = '';
      const flaggedLabels = ['PROFANITY', 'HATE', 'EXTREMIST', 'BOTH'];

      for (const segment of data.segments) {
        const text = segment.text;
        const classification = segment.classification;

        if (flaggedLabels.includes(classification.label) && classification.spans.length > 0) {
          // Highlight replaced spans in green (assuming backend replaces them)
          let highlightedText = text;
          const sortedSpans = [...classification.spans].sort((a, b) => b.char_start - a.char_start);

          for (const span of sortedSpans) {
            const before = highlightedText.substring(0, span.char_start);
            const replaced = highlightedText.substring(span.char_start, span.char_end);
            const after = highlightedText.substring(span.char_end);
            highlightedText = `${before}<span class='text-green-400 font-semibold'>${replaced}</span>${after}`;
          }
          cleanedTranscript += highlightedText + ' ';
        } else {
          cleanedTranscript += text + ' ';
        }
      }

      setCleanTranscript(cleanedTranscript);
      setIsTransforming(false);
      setCurrentStep(3);
    } catch (error) {
      console.error('Error transforming transcript:', error);
      setIsTransforming(false);
      alert('Failed to transform transcript. Make sure the backend server is running.');
    }
  };

  const handleGenerateAudio = async () => {
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('file', file!);
      formData.append('mode', 'negative_output_handling');

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/moderations`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      // Convert base64 audio to blob URL
      if (data.audio && data.audio.data_base64) {
        const audioBytes = atob(data.audio.data_base64);
        const audioArray = new Uint8Array(audioBytes.length);
        for (let i = 0; i < audioBytes.length; i++) {
          audioArray[i] = audioBytes.charCodeAt(i);
        }
        const blob = new Blob([audioArray], { type: data.audio.content_type });
        const audioUrl = URL.createObjectURL(blob);
        setModifiedAudios([audioUrl]);
      }

      setIsProcessing(false);
      setCurrentStep(4);
    } catch (error) {
      console.error('Error generating audio:', error);
      setIsProcessing(false);
      alert('Failed to generate audio. Make sure the backend server is running.');
    }
  };

  const handleStartOver = () => {
    setFile(null);
    setTranscript(null);
    setCleanTranscript(null);
    setModifiedAudios([]);
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
                        Accepted formats: .mp3, .wav, .m4a, .mpeg
                      </p>
                      <input
                        id="audio-upload"
                        type="file"
                        accept=".mp3,.wav,.m4a,.mpeg,audio/*"
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
                      Transcript (Flagged)
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
                      Refined Transcript (Ethically Balanced)
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
              {currentStep === 4 && modifiedAudios.length > 0 && (
                <div
                  key="audio"
                  className="w-full flex flex-col items-center space-y-6"
                >
                  <div className="w-full space-y-6">
                    <h3
                      className="text-3xl font-semibold"
                      style={{ color: accentColor }}
                    >
                      Modified Audio Output
                    </h3>

                    <div className="bg-white/5 border border-white/10 rounded-3xl p-10 w-full max-w-4xl mx-auto space-y-8">
                      {modifiedAudios.map((audioSrc, idx) => (
                        <div key={idx} className="space-y-4">
                          <p className="text-lg font-semibold">
                            Output {idx + 1}
                          </p>

                          <audio
                            controls
                            src={audioSrc}
                            className="w-full h-12 rounded-xl shadow-lg"
                          />

                          <div className="flex justify-center gap-6 pt-6">
                            <a
                              href={audioSrc}
                              download={`modified_audio_${idx + 1}.mpeg`}
                              className="px-10 py-3 bg-white text-black font-semibold rounded-full hover:bg-gray-200 transition shadow-lg"
                            >
                              Download
                            </a>
                            <button
                              onClick={handleStartOver}
                              className="px-10 py-3 bg-white/10 text-white font-semibold rounded-full hover:bg-white/20 transition border border-white/30 shadow-lg"
                            >
                              Start Over
                            </button>
                          </div>
                        </div>
                      ))}
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
