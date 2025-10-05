from __future__ import annotations

import pytest

from app.classification_model.hate_speech_classifier import (
	ClassificationOutput,
	EvidenceSpan,
)
from app.moderation_pipeline import ClassifiedSegment, ModerationResult
from app.negative_output_handling import (
	NegativeHandlingAudio,
	NegativeHandlingProcessing,
	NegativeHandlingSegment,
	run_negative_output_handling,
)


def _make_segment(
	*,
	index: int,
	label: str,
	text: str,
	start: float = 0.0,
	end: float = 1.0,
	speaker: str | None = None,
	spans: list[EvidenceSpan] | None = None,
) -> ClassifiedSegment:
	classification = ClassificationOutput(
		label=label,
		rationale="test rationale",
		spans=spans or [],
		safety={"used_asr_confidence_rule": False, "notes": ""},
	)
	return ClassifiedSegment(
		index=index,
		start=start,
		end=end,
		text=text,
		speaker=speaker,
		classification=classification,
	)


def _make_result(*segments: ClassifiedSegment) -> ModerationResult:
	return ModerationResult(
		transcript="\n".join(segment.text for segment in segments),
		language="en",
		duration=sum(segment.end - segment.start for segment in segments) or None,
		segments=list(segments),
		audio_bytes=b"fake-bytes",
	)


def test_run_negative_output_handling_skips_when_clean() -> None:
	result = _make_result(_make_segment(index=0, label="NONE", text="all good"))

	payload = run_negative_output_handling(
		result,
		source_filename="clean.wav",
	)

	assert payload["status"] == "clean"
	assert payload["summary"]["flagged_segments"] == 0
	assert "processing" not in payload


def test_run_negative_output_handling_aggregates_processing(monkeypatch: pytest.MonkeyPatch) -> None:
	result = _make_result(_make_segment(index=0, label="HATE", text="bad words"))

	fake_processing = NegativeHandlingProcessing(
		success=True,
		processed_segments=1,
		total_segments=1,
		segments=[
			NegativeHandlingSegment(
				index=0,
				start=0.0,
				end=1.0,
				speaker_id="speaker_0",
				original_text="bad words",
				rewritten_text="good words",
				was_rewritten=True,
				offensive_parts=[],
				severity="high",
				generated_audio=NegativeHandlingAudio(
					segment_index=0,
					filename="segment.mp3",
					content_type="audio/mp3",
					data_base64="ZGF0YQ==",
				),
				generated_audio_path=None,
			)
		],
		errors=[],
		metadata=None,
	)

	monkeypatch.setattr(
		"app.negative_output_handling._execute_negative_pipeline",
		lambda *args, **kwargs: fake_processing,
	)

	payload = run_negative_output_handling(
		result,
		source_filename="flagged.wav",
		persist_outputs=False,
	)

	assert payload["status"] == "success"
	assert payload["processing"]["success"] is True
	assert payload["processing"]["segments"][0]["generated_audio"]["filename"] == "segment.mp3"


def test_run_negative_output_handling_marks_partial_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
	result = _make_result(_make_segment(index=0, label="EXTREMIST", text="bad"))

	fake_processing = NegativeHandlingProcessing(
		success=False,
		processed_segments=0,
		total_segments=1,
		segments=[],
		errors=["boom"],
		metadata=None,
	)

	monkeypatch.setattr(
		"app.negative_output_handling._execute_negative_pipeline",
		lambda *args, **kwargs: fake_processing,
	)

	payload = run_negative_output_handling(
		result,
		source_filename="flagged.wav",
		persist_outputs=False,
	)

	assert payload["status"] == "partial"
	assert "processing" in payload
	assert payload["processing"]["errors"] == ["boom"]
	assert "did not complete successfully" in payload["message"]
