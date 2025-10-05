from __future__ import annotations

import os
import tempfile
from http import HTTPStatus
from pathlib import Path
from typing import Optional

from flask import Flask, abort, jsonify, request
from flask_cors import CORS

from .transcription import (
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionService,
    TranscriptionSettings,
    get_settings,
)
from .moderation_pipeline import AudioModerationPipeline
from .negative_output_handling import run_negative_output_handling
import base64

ALLOWED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}


def _validate_audio_file(filename: str | None) -> Path:
    if not filename:
        abort(HTTPStatus.BAD_REQUEST, description="Audio file must include a filename")

    secured = Path(filename).name
    suffix = Path(secured).suffix.lower()
    if suffix and suffix not in ALLOWED_AUDIO_SUFFIXES:
        abort(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            description=f"Unsupported audio format '{suffix}'. Allowed extensions: {', '.join(sorted(ALLOWED_AUDIO_SUFFIXES))}",
        )

    return Path(secured)


def _map_result(result: TranscriptionResult) -> dict[str, object]:
    return {
        "transcript": result.text,
        "segments": [
            {
                "index": segment.index,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            for segment in result.segments
        ],
        "metadata": {
            "language": result.language,
            "duration": result.duration,
            "model": result.model_name,
        },
    }


def _to_bool(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _to_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError as exc:  # pragma: no cover - defensiveness
        abort(HTTPStatus.BAD_REQUEST, description=f"Invalid float value '{value}'")
        raise exc


def create_app(
    *,
    settings: Optional[TranscriptionSettings] = None,
    service: Optional[TranscriptionService] = None,
) -> Flask:
    settings = settings or get_settings()
    app = Flask(__name__)
    CORS(app)
    transcription_service = service or TranscriptionService(settings)

    @app.errorhandler(HTTPStatus.BAD_REQUEST)
    @app.errorhandler(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    def _handle_http_error(exc: Exception):  # type: ignore[override]
        description = getattr(exc, "description", str(exc))
        status_code = getattr(exc, "code", HTTPStatus.INTERNAL_SERVER_ERROR)
        return jsonify({"error": description}), status_code

    @app.post("/transcriptions")
    def create_transcription():
        if "file" not in request.files:
            abort(HTTPStatus.BAD_REQUEST, description="Missing 'file' form-field")

        uploaded = request.files["file"]
        safe_name = _validate_audio_file(uploaded.filename)

        raw_bytes = uploaded.read()
        if not raw_bytes:
            abort(HTTPStatus.BAD_REQUEST, description="Empty audio payload")

        suffix = safe_name.suffix or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw_bytes)
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            options = TranscriptionOptions(
                language=request.form.get("language") or request.args.get("language"),
                translate=_to_bool(request.form.get("translate") or request.args.get("translate")),
                temperature=_to_optional_float(request.form.get("temperature") or request.args.get("temperature")),
                initial_prompt=request.form.get("initial_prompt") or request.args.get("initial_prompt"),
            )
            result = transcription_service.transcribe(tmp_path, options=options)
        finally:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:  # pragma: no cover - double deletion safeguard
                pass

        payload = _map_result(result)
        return jsonify(payload)

    @app.get("/health")
    def healthcheck():
        return jsonify({"status": "ok"})

    @app.post("/moderations")
    def create_moderation():
        """Accept an audio file, run the moderation pipeline, and return classified transcript + audio."""
        if "file" not in request.files:
            abort(HTTPStatus.BAD_REQUEST, description="Missing 'file' form-field")

        uploaded = request.files["file"]
        safe_name = _validate_audio_file(uploaded.filename)

        raw_bytes = uploaded.read()
        if not raw_bytes:
            abort(HTTPStatus.BAD_REQUEST, description="Empty audio payload")

        suffix = safe_name.suffix or ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw_bytes)
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            options = TranscriptionOptions(
                language=request.form.get("language") or request.args.get("language"),
                translate=_to_bool(request.form.get("translate") or request.args.get("translate")),
                temperature=_to_optional_float(request.form.get("temperature") or request.args.get("temperature")),
                initial_prompt=request.form.get("initial_prompt") or request.args.get("initial_prompt"),
            )

            pipeline = AudioModerationPipeline()
            result = pipeline.run(tmp_path, options=options)

            # Serialize result
            segments = []
            for seg in result.segments:
                segments.append(
                    {
                        "index": seg.index,
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "speaker": seg.speaker,
                        "classification": {
                            "label": seg.classification.label,
                            "rationale": seg.classification.rationale,
                            "spans": [
                                {"quote": s.quote, "char_start": s.char_start, "char_end": s.char_end}
                                for s in seg.classification.spans
                            ],
                            "safety": seg.classification.safety,
                        },
                    }
                )

            payload = {
                "transcript": result.transcript,
                "language": result.language,
                "duration": result.duration,
                "segments": segments,
            }

            audio_suffix = safe_name.suffix.lstrip(".") or "wav"
            payload["audio"] = {
                "filename": safe_name.name,
                "content_type": f"audio/{audio_suffix}",
                "data_base64": base64.b64encode(result.audio_bytes).decode("ascii"),
            }

            requested_mode = (request.form.get("mode") or request.args.get("mode") or "").strip().lower()
            if requested_mode in {"extended", "negative", "negative_output", "negative_output_handling", "full"}:
                handler_summary = run_negative_output_handling(
                    result,
                    source_filename=safe_name.name,
                )
                payload["negative_output_handling"] = handler_summary

            return jsonify(payload)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return app


app = create_app()
