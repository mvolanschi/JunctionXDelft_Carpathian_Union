"use client";

import { useEffect, useRef, useState } from "react";
import "../components/VoiceBars.css";

declare global {
  interface Window {
    webkitSpeechRecognition?: any;
    SpeechRecognition?: any;
  }
}

interface VoiceBarsProps {
  barCount?: number;
  keyword?: string;
  lang?: string;
  hitDurationMs?: number;
}

export default function VoiceBars({
  barCount = 120,
  keyword = "danger",
  lang = "en-US",
  hitDurationMs = 1200,
}: VoiceBarsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hit, setHit] = useState(false);

  useEffect(() => {
    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let animationId: number;
    let recognition: any = null;

    async function initAudio() {
      try {
        // 🔑 Request mic access FIRST
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

        // --- audio visualizer setup ---
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        analyser.fftSize = 512;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const bars = containerRef.current
          ?.children as HTMLCollectionOf<HTMLElement>;
        if (!bars || bars.length === 0) return;

        function animate() {
          animationId = requestAnimationFrame(animate);
          analyser!.getByteFrequencyData(dataArray);

          const half = Math.floor(bars.length / 2);

          for (let i = 0; i < bars.length; i++) {
            const distanceFromCenter = Math.abs(i - half);
            const logIndex = Math.floor(
              bufferLength * Math.pow(distanceFromCenter / half, 2)
            );
            const fftIndex = Math.min(bufferLength - 1, logIndex);

            const value = dataArray[fftIndex] || 0;
            const percent = value / 255;
            const scale = percent > 0 ? percent * 3 : 0;

            const bar = bars[i];
            bar.style.transform = `scaleY(${scale})`;
          }
        }

        animate();

        // --- speech recognition setup ---
        const SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognition) {
          recognition = new SpeechRecognition();
          recognition.lang = lang;
          recognition.continuous = true;
          recognition.interimResults = false;

          recognition.onresult = (event: SpeechRecognitionEvent) => {
            const transcript = event.results[
              event.results.length - 1
            ][0].transcript
              .trim()
              .toLowerCase();

            console.log("🎤 Heard:", transcript);

            if (transcript.includes(keyword.toLowerCase())) {
              setHit(true);
              setTimeout(() => setHit(false), hitDurationMs);
            }
          };

          recognition.onerror = (err: any) =>
            console.error("Speech error:", err);
          recognition.onend = () => recognition.start(); // auto-restart

          recognition.start();
        } else {
          console.error("❌ SpeechRecognition not supported in this browser");
        }
      } catch (err) {
        console.error("❌ Mic access denied or error:", err);
      }
    }

    initAudio();

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      if (audioContext) audioContext.close();
      recognition?.stop();
    };
  }, [barCount, keyword, lang, hitDurationMs]);

  return (
    <div ref={containerRef} className={`voice-coder ${hit ? "hit" : ""}`}>
      {Array.from({ length: barCount }).map((_, i) => (
        <span key={i} />
      ))}
    </div>
  );
}
