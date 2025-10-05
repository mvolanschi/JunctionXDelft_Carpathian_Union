"use client";

import { useEffect, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import Orb from "@/components/Orb";
import VoiceBars from "@/components/VoiceBars";
import ElectricBorder from "@/components/ElectricBorder";

type ClassificationSpan = {
  quote: string;
  char_start?: number;
  char_end?: number;
};

type Classification = {
  label: string;
  spans: ClassificationSpan[];
  rationale: string;
};

type ModerationSegment = {
  index: number;
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
  classification: Classification;
};

type NegativeHandlingSummary = {
  total_segments: number;
  flagged_segments: number;
  flagged_indexes: number[];
  label_counts: Record<string, number>;
};

type NegativeHandlingAudio = {
  segment_index: number;
  filename: string;
  content_type: string;
  data_base64: string;
};

type NegativeHandlingSegment = {
  index: number;
  start: number;
  end: number;
  speaker_id: string;
  original_text: string;
  rewritten_text: string;
  was_rewritten: boolean;
  generated_audio?: NegativeHandlingAudio;
};

type NegativeHandlingProcessing = {
  success: boolean;
  processed_segments: number;
  total_segments: number;
  segments: NegativeHandlingSegment[];
  errors: string[];
  metadata?: Record<string, unknown>;
};

type NegativeHandlingReport = {
  status: string;
  summary: NegativeHandlingSummary;
  message?: string;
  processing?: NegativeHandlingProcessing;
};

type ModerationResponse = {
  transcript: string;
  language: string;
  duration: number | null;
  segments: ModerationSegment[];
  audio: {
    filename: string;
    content_type: string;
    data_base64: string;
  };
  negative_output_handling?: NegativeHandlingReport;
};

type GeneratedSegment = {
  segmentIndex: number;
  originalText: string;
  rewrittenText: string;
  audioUrl: string;
  filename: string;
  contentType: string;
};

const FLAGGED_LABELS = new Set(["HATE", "PROFANITY", "EXTREMIST", "BOTH"]);

type NormalizedSpan = {
  start: number;
  end: number;
};

function normalizeSpans(text: string, spans: ClassificationSpan[] | undefined): NormalizedSpan[] {
  if (!spans || spans.length === 0) {
    return [];
  }

  const max = text.length;

  const normalized = spans
    .map((span) => {
      if (typeof span.char_start !== "number" || typeof span.char_end !== "number") {
        return null;
      }
      const start = Math.max(0, Math.min(max, Math.floor(span.char_start)));
      const end = Math.max(0, Math.min(max, Math.ceil(span.char_end + 1)));
      if (end <= start) {
        return null;
      }
      return { start, end } satisfies NormalizedSpan;
    })
    .filter((span): span is NormalizedSpan => span !== null)
    .sort((a, b) => a.start - b.start);

  if (normalized.length <= 1) {
    return normalized;
  }

  const merged: NormalizedSpan[] = [];
  normalized.forEach((span) => {
    const last = merged[merged.length - 1];
    if (!last || span.start > last.end) {
      let adjustedStart = span.start;
      while (adjustedStart > 0 && text[adjustedStart - 1] === " ") {
        adjustedStart -= 1;
      }

      let adjustedEnd = span.end;
      while (adjustedEnd < text.length && text[adjustedEnd] === " ") {
        adjustedEnd += 1;
      }

      merged.push({ ...span });
      merged[merged.length - 1].start = adjustedStart;
      merged[merged.length - 1].end = adjustedEnd;
      return;
    }
    let combinedEnd = Math.max(last.end, span.end);
    while (combinedEnd < text.length && text[combinedEnd] === " ") {
      combinedEnd += 1;
    }
    last.end = combinedEnd;
  });

  return merged;
}

function formatSpeaker(segment: ModerationSegment, index: number): string {
  const label = segment.speaker ?? "";
  if (label.trim().length > 0) {
    return label;
  }
  return `Speaker ${index + 1}`;
}

function formatTimeRange(start: number, end: number): string {
  const safeStart = Number.isFinite(start) ? start : 0;
  const safeEnd = Number.isFinite(end) ? end : safeStart;
  return `${safeStart.toFixed(1)}s – ${safeEnd.toFixed(1)}s`;
}

function renderSegmentContent(segment: ModerationSegment, spans: NormalizedSpan[]): ReactNode {
  const text = segment.text ?? "";

  if (spans.length === 0) {
    if (FLAGGED_LABELS.has(segment.classification.label)) {
      return (
        <span className="inline rounded-lg bg-red-500/20 px-1.5 py-0.5 font-semibold text-red-100 shadow-[0_0_18px_rgba(248,113,113,0.25)]">
          {text}
        </span>
      );
    }
    return text;
  }

  const nodes: ReactNode[] = [];
  let cursor = 0;

  spans.forEach((span, idx) => {
    const start = Math.max(cursor, span.start);
    const end = Math.max(start, span.end);

    if (start > cursor) {
      nodes.push(text.slice(cursor, start));
    }

    if (end > start) {
      nodes.push(
        <span
          key={`segment-${segment.index}-span-${idx}`}
          className="inline rounded-lg bg-red-500/25 px-1.5 py-0.5 font-semibold text-red-100 shadow-[0_0_18px_rgba(248,113,113,0.35)]"
        >
          {text.slice(start, end)}
        </span>,
      );
    }

    cursor = end;
  });

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }

  return nodes;
}

function renderTranscriptParagraph(segments: ModerationSegment[]): ReactNode {
  if (!segments || segments.length === 0) {
    return null;
  }

  const nodes: ReactNode[] = [];
  let previousSpeaker: string | null = null;

  segments.forEach((segment, idx) => {
    const spans = normalizeSpans(segment.text ?? "", segment.classification.spans);
    const speakerLabel = formatSpeaker(segment, idx);
    const timeRange = formatTimeRange(segment.start, segment.end);
    const isFlagged = spans.length > 0 || FLAGGED_LABELS.has(segment.classification.label);

    if (idx > 0) {
      nodes.push(" ");
    }

    const showSpeaker = idx === 0 || speakerLabel !== previousSpeaker;
    if (showSpeaker) {
      nodes.push(
        <span
          key={`segment-${segment.index ?? idx}-meta`}
          className="mr-2 inline text-[0.65rem] uppercase tracking-[0.3em] text-white/40"
        >
          {speakerLabel} ({timeRange})
        </span>,
      );
      previousSpeaker = speakerLabel;
    }

    if (isFlagged) {
      nodes.push(
        <span
          key={`segment-${segment.index ?? idx}-label`}
          className="mr-2 inline rounded-full border border-red-400/40 bg-red-500/10 px-2 py-0.5 text-[0.6rem] font-semibold uppercase tracking-[0.25em] text-red-200"
        >
          {segment.classification.label || "UNLABELED"}
        </span>,
      );
    }

    nodes.push(
      <span
        key={`segment-${segment.index ?? idx}-text`}
        className="inline text-base leading-7 text-white/80"
      >
        {renderSegmentContent(segment, spans)}
      </span>,
    );
  });

  return nodes;
}

function renderCleanParagraph(segments: NegativeHandlingSegment[]): ReactNode {
  if (!segments || segments.length === 0) {
    return null;
  }

  const nodes: ReactNode[] = [];
  let previousSpeaker: string | null = null;

  segments.forEach((segment, idx) => {
    const speakerId = segment.speaker_id && segment.speaker_id.trim().length > 0 ? segment.speaker_id : `Speaker ${idx + 1}`;

    if (idx > 0) {
      nodes.push(" ");
    }

    const showSpeaker = idx === 0 || speakerId !== previousSpeaker;
    if (showSpeaker) {
      nodes.push(
        <span
          key={`clean-${segment.index ?? idx}-meta`}
          className="mr-2 inline text-[0.65rem] uppercase tracking-[0.3em] text-white/40"
        >
          {speakerId}
        </span>,
      );
      previousSpeaker = speakerId;
    }

    nodes.push(
      <span
        key={`clean-${segment.index ?? idx}-text`}
        className="inline text-base leading-7 text-white/80"
      >
        {segment.was_rewritten ? (
          <span className="inline rounded-lg bg-emerald-500/20 px-1.5 py-0.5 font-semibold text-emerald-200 shadow-[0_0_18px_rgba(52,211,153,0.25)]">
            {segment.rewritten_text}
          </span>
        ) : (
          segment.original_text
        )}
      </span>,
    );
  });

  return nodes;
}

function base64ToObjectUrl(base64: string, contentType: string): string {
  const binary = atob(base64);
  const length = binary.length;
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: contentType || "audio/wav" });
  return URL.createObjectURL(blob);
}

export default function GetStartedPage() {
  const accentColor = "#4cc9f0";
  const [file, setFile] = useState<File | null>(null);
  const [flaggedSegments, setFlaggedSegments] = useState<ModerationSegment[] | null>(null);
  const [cleanSegments, setCleanSegments] = useState<NegativeHandlingSegment[] | null>(null);
  const [generatedSegments, setGeneratedSegments] = useState<GeneratedSegment[]>([]);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<NegativeHandlingSummary | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    return () => {
      generatedSegments.forEach((segment) => URL.revokeObjectURL(segment.audioUrl));
    };
  }, [generatedSegments]);

  useEffect(() => {
    if (!file) {
      setAudioPreviewUrl((previous) => {
        if (previous) {
          URL.revokeObjectURL(previous);
        }
        return null;
      });
      return;
    }

    const url = URL.createObjectURL(file);
    setAudioPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setGeneratedSegments((prev) => {
        prev.forEach((segment) => URL.revokeObjectURL(segment.audioUrl));
        return [];
      });
      setFlaggedSegments(null);
      setCleanSegments(null);
      setCurrentStep(1);
      setError(null);
      setSummary(null);
    }
  };

  const handleProcess = async () => {
    if (!file) {
      return;
    }

    setIsProcessing(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${apiBase}/moderations`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`);
      }

      const data = (await response.json()) as ModerationResponse;
      setFlaggedSegments(data.segments ?? []);

      const negative = data.negative_output_handling;
      const cleaned = negative?.processing?.segments ?? null;
      setCleanSegments(cleaned && cleaned.length > 0 ? cleaned : null);
      setSummary(negative?.summary ?? null);

      if (cleaned && cleaned.length > 0) {
        setGeneratedSegments((prev) => {
          prev.forEach((segment) => URL.revokeObjectURL(segment.audioUrl));
          const next = cleaned
            .filter((segment) => segment.generated_audio)
            .map((segment) => {
              const audio = segment.generated_audio!;
              return {
                segmentIndex: segment.index,
                originalText: segment.original_text,
                rewrittenText: segment.rewritten_text,
                audioUrl: base64ToObjectUrl(audio.data_base64, audio.content_type),
                filename: audio.filename,
                contentType: audio.content_type,
              } satisfies GeneratedSegment;
            });
          return next;
        });
      } else {
        setGeneratedSegments((prev) => {
          prev.forEach((segment) => URL.revokeObjectURL(segment.audioUrl));
          return [];
        });
      }

      setCurrentStep(2);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected error while processing audio.";
      setError(message);
      setFlaggedSegments(null);
      setCleanSegments(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTransform = () => {
    if (!cleanSegments) {
      return;
    }
    setCurrentStep(3);
  };

  const handleGenerateAudio = () => {
    if (generatedSegments.length === 0) {
      return;
    }
    setCurrentStep(4);
  };

  const handleStartOver = () => {
    setFile(null);
    setFlaggedSegments(null);
    setCleanSegments(null);
    setGeneratedSegments((prev) => {
      prev.forEach((segment) => URL.revokeObjectURL(segment.audioUrl));
      return [];
    });
    setAudioPreviewUrl((previous) => {
      if (previous) {
        URL.revokeObjectURL(previous);
      }
      return null;
    });
    setCurrentStep(1);
    setError(null);
    setSummary(null);
  };

  const hasCleanSegments = Boolean(cleanSegments && cleanSegments.length > 0);

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-black text-white">
      <VoiceBars keyword="upload" />
      <Orb hoverIntensity={0.5} rotateOnHover hue={0} forceHoverState={false} />

      <div className="relative z-10 flex w-full max-w-4xl flex-col items-center space-y-8 px-6 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight text-white drop-shadow-[0_0_25px_rgba(255,255,255,0.8)] md:text-6xl">
          Upload &amp; Transform
        </h1>
        <p className="max-w-2xl text-lg font-semibold text-white drop-shadow-[0_0_20px_rgba(255,255,255,0.5)] md:text-xl">
          Upload your audio file — we&rsquo;ll analyze, flag, and ethically transform its content.
        </p>

        <ElectricBorder color={accentColor} speed={3} chaos={2}>
          <div className="flex w-full flex-col items-center justify-center space-y-6 rounded-3xl bg-black/80 p-10">
            {error && (
              <div className="w-full rounded-2xl border border-red-400/60 bg-red-500/20 px-4 py-3 text-left text-red-200">
                <p className="font-semibold">We couldn&rsquo;t process that audio.</p>
                <p className="mt-1 text-sm text-red-100/80">{error}</p>
              </div>
            )}
            <AnimatePresence mode="wait">
              {currentStep === 1 && (
                <div key="upload" className="flex w-full flex-col items-center space-y-6">
                  {!file ? (
                    <label
                      htmlFor="audio-upload"
                      className="flex h-40 w-full cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-white/40 transition hover:bg-white/10"
                    >
                      <p className="mb-2 text-lg text-white/70">Click or drag to upload</p>
                      <p className="text-sm text-gray-400">Accepted formats: .mp3, .wav, .m4a, .mpeg</p>
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
                        className="rounded-full bg-white px-8 py-3 font-semibold text-black shadow-lg transition hover:bg-gray-200"
                      >
                        {isProcessing ? "Processing..." : "Process Audio"}
                      </Button>
                    </>
                  )}
                </div>
              )}

              {currentStep === 2 && flaggedSegments !== null && (
                <div key="transcript" className="flex w-full flex-col items-center space-y-6">
                  <div className="w-full space-y-4 text-left">
                    <div className="flex items-center justify-between">
                      <h3 className="text-2xl font-semibold" style={{ color: accentColor }}>
                        Transcript (Flagged)
                      </h3>
                      <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-white/60">
                        Extended Pipeline
                      </span>
                    </div>
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-left shadow-[0_0_25px_rgba(248,113,113,0.15)]">
                      {flaggedSegments.length === 0 ? (
                        <p className="text-sm text-white/60">No transcript segments were returned.</p>
                      ) : (
                        <p className="whitespace-pre-wrap text-left text-base leading-7 text-white/80">
                          {renderTranscriptParagraph(flaggedSegments)}
                        </p>
                      )}
                    </div>
                    {audioPreviewUrl && (
                      <div className="mt-4">
                        <audio controls src={audioPreviewUrl} className="w-full rounded-lg shadow-lg" />
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={handleTransform}
                    disabled={!hasCleanSegments}
                    className="rounded-full bg-white px-8 py-3 font-semibold text-black shadow-lg transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:bg-white/40 disabled:text-white/70"
                  >
                    {hasCleanSegments ? "Transform Transcript" : "No Transform Needed"}
                  </Button>
                </div>
              )}

              {currentStep === 3 && cleanSegments && (
                <div key="refined" className="flex w-full flex-col items-center space-y-6">
                  <div className="w-full space-y-4 text-left">
                    <h3 className="text-2xl font-semibold" style={{ color: accentColor }}>
                      Refined Transcript (Ethically Balanced)
                    </h3>
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-left shadow-[0_0_25px_rgba(16,185,129,0.15)]">
                      <p className="whitespace-pre-wrap text-left text-base leading-7 text-white/80">
                        {renderCleanParagraph(cleanSegments)}
                      </p>
                    </div>
                    {summary && (
                      <div className="mt-4 rounded-xl border border-white/10 bg-black/60 p-4">
                        <p className="text-sm uppercase tracking-widest text-white/40">Extended summary</p>
                        <p className="mt-2 text-white/80">
                          Flagged segments: <span className="font-semibold">{summary.flagged_segments}</span> / {summary.total_segments}
                        </p>
                        <p className="mt-2 text-sm text-white/60">
                          Labels: {Object.entries(summary.label_counts).length > 0
                            ? Object.entries(summary.label_counts)
                                .map(([label, count]) => `${label}: ${count}`)
                                .join(", ")
                            : "None"}
                        </p>
                      </div>
                    )}
                  </div>
                  <Button
                    onClick={handleGenerateAudio}
                    disabled={generatedSegments.length === 0}
                    className="rounded-full bg-white px-8 py-3 font-semibold text-black shadow-lg transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:bg-white/40 disabled:text-white/70"
                  >
                    {generatedSegments.length === 0 ? "No Audio Generated" : "Generate Modified Audio"}
                  </Button>
                </div>
              )}

              {currentStep === 4 && generatedSegments.length > 0 && (
                <div key="audio" className="flex w-full flex-col items-center space-y-6">
                  <div className="w-full space-y-6">
                    <h3 className="text-3xl font-semibold" style={{ color: accentColor }}>
                      Modified Audio Output
                    </h3>

                    <div className="mx-auto w-full max-w-4xl space-y-8 rounded-3xl border border-white/10 bg-white/5 p-10">
                      {generatedSegments.map((segment, idx) => (
                        <div key={idx} className="space-y-4">
                          <p className="text-lg font-semibold">Output {idx + 1}</p>

                          <div className="space-y-2 rounded-xl border border-white/10 bg-black/60 p-4 text-left">
                            <p className="text-sm text-white/60">Original: {segment.originalText}</p>
                            <p className="text-sm text-emerald-300">Rewritten: {segment.rewrittenText}</p>
                          </div>

                          <audio controls src={segment.audioUrl} className="h-12 w-full rounded-xl shadow-lg" />

                          <div className="flex justify-center gap-6 pt-6">
                            <a
                              href={segment.audioUrl}
                              download={segment.filename || `modified_audio_${idx + 1}`}
                              className="rounded-full bg-white px-10 py-3 font-semibold text-black shadow-lg transition hover:bg-gray-200"
                            >
                              Download
                            </a>
                            <button
                              onClick={handleStartOver}
                              className="rounded-full border border-white/30 bg-white/10 px-10 py-3 font-semibold text-white shadow-lg transition hover:bg-white/20"
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
