from __future__ import annotations

import asyncio
import base64
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .moderation_pipeline import ClassifiedSegment, ModerationResult

_FLAGGED_LABEL_SEVERITY: dict[str, str] = {
    "HATE": "high",
    "PROFANITY": "medium",
    "EXTREMIST": "high",
    "BOTH": "high",
}

_FLAGGED_LABELS: set[str] = set(_FLAGGED_LABEL_SEVERITY)


@dataclass(slots=True)
class NegativeHandlingSummary:
    total_segments: int
    flagged_segments: int
    flagged_indexes: list[int]
    label_counts: dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NegativeHandlingAudio:
    segment_index: int
    filename: str
    content_type: str
    data_base64: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NegativeHandlingSegment:
    index: int
    start: float
    end: float
    speaker_id: str
    original_text: str
    rewritten_text: str
    was_rewritten: bool
    offensive_parts: list[Dict[str, Any]]
    severity: Optional[str]
    generated_audio: Optional[NegativeHandlingAudio] = None
    generated_audio_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.generated_audio is None:
            payload.pop("generated_audio")
        else:
            payload["generated_audio"] = self.generated_audio.to_dict()
        if self.generated_audio_path is None:
            payload.pop("generated_audio_path")
        return payload


@dataclass(slots=True)
class NegativeHandlingProcessing:
    success: bool
    processed_segments: int
    total_segments: int
    segments: list[NegativeHandlingSegment]
    errors: list[str]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": self.success,
            "processed_segments": self.processed_segments,
            "total_segments": self.total_segments,
            "segments": [segment.to_dict() for segment in self.segments],
            "errors": list(self.errors),
        }
        if self.metadata is not None:
            payload["metadata"] = self.metadata
        return payload


@dataclass(slots=True)
class NegativeHandlingReport:
    status: str
    summary: NegativeHandlingSummary
    message: Optional[str] = None
    processing: Optional[NegativeHandlingProcessing] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "status": self.status,
            "summary": self.summary.to_dict(),
        }
        if self.message:
            payload["message"] = self.message
        if self.processing:
            payload["processing"] = self.processing.to_dict()
        return payload


class NegativeOutputHandlingUnavailable(Exception):
    """Raised when the optional NegativeOutputHandling component cannot be loaded."""


def run_negative_output_handling(
    result: ModerationResult,
    *,
    source_filename: str,
    output_root: Path | None = None,
    persist_outputs: bool | None = None,
) -> Dict[str, Any]:
    """Run the optional NegativeOutputHandling pipeline for a moderation result.

    Parameters
    ----------
    result:
        Moderation result produced by :class:`AudioModerationPipeline`.
    source_filename:
        Original filename of the audio payload. Used to infer file extensions when
        persisting audio to disk for the NegativeOutputHandling pipeline.
    output_root:
        Optional directory where enhanced artefacts should be created when
        persistence is enabled. If omitted, the pipeline operates entirely
        in-memory.
    persist_outputs:
        When ``True`` (or when ``output_root`` is provided), the extended pipeline
        also materialises cleaned JSON/audio files on disk alongside returning the
        structured response. Defaults to ``False`` for API-friendly in-memory
        operation.

    Returns
    -------
    dict
        A JSON-serialisable dictionary describing the NegativeOutputHandling
        outcome. The dictionary always contains the keys ``status`` and
        ``summary``. When the extended pipeline executes successfully the result
        also contains a ``processing`` section enumerating the rewritten
        segments, including optional base64-encoded audio renderings. Set
        ``persist_outputs`` to ``True`` to additionally write JSON/audio files
        to ``output_root`` (when provided) for offline inspection.
    """

    summary = _build_summary(result)
    report = NegativeHandlingReport(
        status="clean" if summary.flagged_segments == 0 else "pending",
        summary=summary,
    )

    if summary.flagged_segments == 0:
        report.message = "No offensive segments detected; skipped NegativeOutputHandling."
        return report.to_dict()

    try:
        processing = _execute_negative_pipeline(
            result,
            source_filename=source_filename,
            output_root=output_root,
            persist_outputs=persist_outputs,
        )
    except NegativeOutputHandlingUnavailable as exc:
        report.status = "unavailable"
        report.message = str(exc)
        return report.to_dict()
    except Exception as exc:  # pragma: no cover - defensive catch
        report.status = "error"
        report.message = f"Failed to run NegativeOutputHandling: {exc}"
        return report.to_dict()

    report.processing = processing
    report.status = "success" if processing.success else "partial"
    if not processing.success and not report.message:
        report.message = (
            "NegativeOutputHandling pipeline executed but did not complete successfully."
        )
    return report.to_dict()


def _build_summary(result: ModerationResult) -> NegativeHandlingSummary:
    label_counts: Dict[str, int] = {}
    flagged_indexes: list[int] = []

    for segment in result.segments:
        label = segment.classification.label
        label_counts[label] = label_counts.get(label, 0) + 1
        if label in _FLAGGED_LABELS:
            flagged_indexes.append(segment.index)

    return NegativeHandlingSummary(
        total_segments=len(result.segments),
        flagged_segments=len(flagged_indexes),
        flagged_indexes=flagged_indexes,
        label_counts=label_counts,
    )


def _execute_negative_pipeline(
    result: ModerationResult,
    *,
    source_filename: str,
    output_root: Path | None,
    persist_outputs: bool | None,
) -> NegativeHandlingProcessing:
    speech_processor = _import_speech_processor()

    backend_root = Path(__file__).resolve().parents[1]
    if persist_outputs is None:
        persist_outputs = output_root is not None

    effective_output = output_root or backend_root / "NegativeOutputHandling" / "Data" / "api_runs"
    if persist_outputs:
        effective_output.mkdir(parents=True, exist_ok=True)

    payload = _convert_to_processing_json(result, source_filename)

    suffix = Path(source_filename).suffix or ".wav"

    with tempfile.TemporaryDirectory(prefix="negative_output_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        audio_path = tmpdir_path / f"reference{suffix}"
        audio_path.write_bytes(result.audio_bytes)

        json_path = tmpdir_path / "input.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        processor = speech_processor.SpeechProcessor(
            input_json_path=str(json_path),
            reference_audio_path=str(audio_path),
            output_dir=str(effective_output),
            persist_outputs=persist_outputs,
        )

        processing_result = _run_coroutine(processor.process_complete())
    data = processing_result.data or {}
    segments_data = data.get("segments", [])
    metadata = data.get("processing_info")

    audio_map = {
        audio.segment_index: audio
        for audio in (processing_result.generated_audio or [])
    }

    original_segments: Dict[int, ClassifiedSegment] = {seg.index: seg for seg in result.segments}
    segments_payload: list[NegativeHandlingSegment] = []

    for idx, segment in enumerate(segments_data):
        segment_index = int(segment.get("segment_index", idx))
        origin = original_segments.get(segment_index)

        speaker_id = segment.get("speaker_id") or (origin.speaker if origin else f"speaker_{segment_index:03d}")
        original_text = segment.get("original_text") or (origin.text if origin else segment.get("text", ""))
        rewritten_text = segment.get("text", "")
        was_rewritten = bool(segment.get("was_rewritten"))
        offensive_parts = list(segment.get("offensive_parts", []))
        severity = _map_severity(origin.classification.label) if origin else None

        audio_payload = audio_map.get(segment_index)
        generated_audio = None
        generated_audio_path: Optional[str] = None
        if audio_payload is not None:
            generated_audio = NegativeHandlingAudio(
                segment_index=segment_index,
                filename=audio_payload.filename,
                content_type=audio_payload.content_type,
                data_base64=base64.b64encode(audio_payload.data).decode("ascii"),
            )
        elif segment.get("generated_audio_file"):
            generated_audio_path = str((effective_output / segment["generated_audio_file"]).resolve())

        segments_payload.append(
            NegativeHandlingSegment(
                index=segment_index,
                start=float(segment.get("start", origin.start if origin else 0.0)),
                end=float(segment.get("end", origin.end if origin else 0.0)),
                speaker_id=str(speaker_id),
                original_text=str(original_text),
                rewritten_text=str(rewritten_text),
                was_rewritten=was_rewritten,
                offensive_parts=offensive_parts,
                severity=severity,
                generated_audio=generated_audio,
                generated_audio_path=generated_audio_path,
            )
        )

    errors = [str(err) for err in (processing_result.errors or [])]

    return NegativeHandlingProcessing(
        success=bool(processing_result.success),
        processed_segments=processing_result.processed_segments,
        total_segments=processing_result.total_segments,
        segments=segments_payload,
        errors=errors,
        metadata=metadata,
    )


def _import_speech_processor() -> Any:
    backend_root = Path(__file__).resolve().parents[1]
    code_dir = backend_root / "NegativeOutputHandling" / "Code"
    if not code_dir.exists():
        raise NegativeOutputHandlingUnavailable(
            "NegativeOutputHandling/Code directory not found; extended pipeline unavailable.",
        )

    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))

    try:
        import speech_processor  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure guard
        raise NegativeOutputHandlingUnavailable(
            f"Unable to import NegativeOutputHandling speech processor: {exc}",
        ) from exc

    if not hasattr(speech_processor, "SpeechProcessor"):
        raise NegativeOutputHandlingUnavailable(
            "NegativeOutputHandling speech_processor module missing SpeechProcessor class.",
        )

    return speech_processor


def _convert_to_processing_json(result: ModerationResult, source_filename: str) -> Dict[str, Any]:
    speakers: Dict[str, str] = {}
    segments_payload: list[Dict[str, Any]] = []

    for segment in result.segments:
        speaker_id = segment.speaker or f"speaker_{segment.index:03d}"
        speakers.setdefault(speaker_id, speaker_id.replace("_", " ").title())

        offensive_parts = _build_offensive_parts(segment)

        segments_payload.append(
            {
                "segment_index": segment.index,
                "start": segment.start,
                "end": segment.end,
                "speaker_id": speaker_id,
                "text": segment.text,
                "original_text": segment.text,
                "offensive_parts": offensive_parts,
            }
        )

    return {
        "speakers": speakers,
        "segments": segments_payload,
        "metadata": {
            "original_transcript": result.transcript,
            "language": result.language,
            "duration": result.duration,
            "audio_filename": source_filename,
            "source": "moderation_pipeline",
        },
    }


def _build_offensive_parts(segment: ClassifiedSegment) -> list[Dict[str, Any]]:
    if segment.classification.label not in _FLAGGED_LABELS:
        return []

    spans = segment.classification.spans
    severity = _map_severity(segment.classification.label)

    if spans:
        return [
            {
                "start": segment.start,
                "end": segment.end,
                "text": span.quote,
                "severity": severity,
                "char_start": span.char_start,
                "char_end": span.char_end,
                "rationale": segment.classification.rationale,
            }
            for span in spans
        ]

    return [
        {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "severity": severity,
            "rationale": segment.classification.rationale,
        }
    ]


def _map_severity(label: str) -> str:
    return _FLAGGED_LABEL_SEVERITY.get(label, "low")


def _run_coroutine(coro: Any) -> Any:
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:  # pragma: no cover - only triggered in nested loops
        if "already running" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
