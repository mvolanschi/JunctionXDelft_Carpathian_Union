#!/usr/bin/env python3
"""
Hate Speech and Extremist Content Classifier using Llama 3.3 via Groq API.
Classifies audio transcript segments according to specified policy.
"""

import json
import os
import re
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from groq import Groq
import jsonschema
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class ClassificationInput:
    segment_text: str
    segment_start: float
    segment_end: float
    asr_mean_confidence: float
    confidence_threshold: float = 0.45


@dataclass
class EvidenceSpan:
    quote: str
    char_start: int
    char_end: int


@dataclass
class ClassificationOutput:
    label: str
    rationale: str
    spans: List[EvidenceSpan]
    safety: Dict[str, Any]


class HateSpeechClassifier:
    LABELS = ["NONE", "PROFANITY", "HATE", "EXTREMIST", "BOTH", "UNCLEAR", "UNCLEAR_ASR"]
    
    @classmethod
    def _get_system_prompt(cls) -> str:
        return f"""You are a deterministic content classifier for English ASR transcript segments.
Return ONLY valid JSON that conforms to the provided schema.

POLICY
- PROFANITY: swearing/insults not targeting a protected class.
- HATE: derogation, dehumanization, or threats toward a protected class.
- EXTREMIST: praise/propaganda/recruitment for violent extremist orgs/ideologies; calls to violence; explicit support for terrorism/violent acts.
- BOTH: contains both HATE and EXTREMIST.
- NONE: none of the above.
- UNCLEAR: ambiguous/quoted/satire.
- UNCLEAR_ASR: ASR confidence < threshold.

RULES
- Use only the segment text provided.
- Quote exact substrings as evidence spans with character indices.
- If confidence < threshold → UNCLEAR_ASR.

EXAMPLES:

Example 1 (NONE):
Input: {{"segment_text": "The design is flawed, but I see their point.", "asr_mean_confidence": 0.92, "confidence_threshold": 0.45}}
Output: {{"label": "NONE", "rationale": "Contains criticism but no profanity, hate speech, or extremist content.", "spans": [], "safety": {{"used_asr_confidence_rule": false, "notes": ""}}}}

Example 2 (PROFANITY):
Input: {{"segment_text": "This app is freaking useless. What a dumb idea.", "asr_mean_confidence": 0.86, "confidence_threshold": 0.45}}
Output: {{"label": "PROFANITY", "rationale": "Contains insults and profanity without targeting a protected class.", "spans": [{{"quote": "freaking useless", "char_start": 13, "char_end": 29}}, {{"quote": "dumb idea", "char_start": 38, "char_end": 47}}], "safety": {{"used_asr_confidence_rule": false, "notes": ""}}}}

Example 3 (HATE):
Input: {{"segment_text": "People with disabilities don't belong in tech.", "asr_mean_confidence": 0.88, "confidence_threshold": 0.45}}
Output: {{"label": "HATE", "rationale": "Targets people with disabilities (protected class) with discriminatory exclusion.", "spans": [{{"quote": "People with disabilities don't belong in tech", "char_start": 0, "char_end": 46}}], "safety": {{"used_asr_confidence_rule": false, "notes": ""}}}}

Example 4 (EXTREMIST):
Input: {{"segment_text": "Join the cause and make them afraid on voting day.", "asr_mean_confidence": 0.79, "confidence_threshold": 0.45}}
Output: {{"label": "EXTREMIST", "rationale": "Calls for intimidation tactics around voting, promoting fear-based extremist actions.", "spans": [{{"quote": "make them afraid on voting day", "char_start": 19, "char_end": 50}}], "safety": {{"used_asr_confidence_rule": false, "notes": ""}}}}

Example 5 (BOTH):
Input: {{"segment_text": "Drive them out and burn their temples; those people are a disease.", "asr_mean_confidence": 0.84, "confidence_threshold": 0.45}}
Output: {{"label": "BOTH", "rationale": "Contains both hate speech (dehumanizing language) and extremist content (calls to violence).", "spans": [{{"quote": "Drive them out and burn their temples", "char_start": 0, "char_end": 38}}, {{"quote": "those people are a disease", "char_start": 40, "char_end": 66}}], "safety": {{"used_asr_confidence_rule": false, "notes": ""}}}}

Example 6 (UNCLEAR):
Input: {{"segment_text": "He read: \\"Group Z urged attacks\\" and then condemned it strongly.", "asr_mean_confidence": 0.95, "confidence_threshold": 0.45}}
Output: {{"label": "UNCLEAR", "rationale": "Contains quoted extremist content but speaker is condemning it, making classification ambiguous.", "spans": [], "safety": {{"used_asr_confidence_rule": false, "notes": ""}}}}

Example 7 (UNCLEAR_ASR):
Input: {{"segment_text": "j.. j.. *noise* ... them now ...", "asr_mean_confidence": 0.31, "confidence_threshold": 0.45}}
Output: {{"label": "UNCLEAR_ASR", "rationale": "ASR confidence 0.31 below threshold 0.45", "spans": [], "safety": {{"used_asr_confidence_rule": true, "notes": "Low ASR confidence, abstaining from classification"}}}}

JSON SCHEMA:
{json.dumps(cls.OUTPUT_SCHEMA, indent=2)}"""

    OUTPUT_SCHEMA = {
        "type": "object",
        "required": ["label", "rationale", "spans", "safety"],
        "properties": {
            "label": {
                "type": "string",
                "enum": LABELS
            },
            "rationale": {
                "type": "string",
                "maxLength": 500
            },
            "spans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["quote", "char_start", "char_end"],
                    "properties": {
                        "quote": {"type": "string"},
                        "char_start": {"type": "integer", "minimum": 0},
                        "char_end": {"type": "integer", "minimum": 0}
                    }
                }
            },
            "safety": {
                "type": "object",
                "required": ["used_asr_confidence_rule", "notes"],
                "properties": {
                    "used_asr_confidence_rule": {"type": "boolean"},
                    "notes": {"type": "string"}
                }
            }
        }
    }

    def __init__(self, api_key: Optional[str] = None):
        self.client = Groq(api_key=api_key or os.getenv("GROQ_API_KEY"))
        
    def classify(self, input_data: ClassificationInput) -> ClassificationOutput:
        """Classify a transcript segment for hate speech and extremist content."""
        
        # Prepare input JSON
        input_json = {
            "segment_text": input_data.segment_text,
            "segment_start": input_data.segment_start,
            "segment_end": input_data.segment_end,
            "asr_mean_confidence": input_data.asr_mean_confidence,
            "confidence_threshold": input_data.confidence_threshold
        }
        
        # Create user prompt
        user_prompt = f"Input:\n{json.dumps(input_json, indent=2)}"
        
        # Call Groq API
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                top_p=0.0,
                max_tokens=256,
                seed=42  # Fixed seed for reproducibility
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Validate JSON format
            try:
                response_json = json.loads(response_text)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response if wrapped in markdown
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(1))
                else:
                    raise ValueError(f"Invalid JSON response: {e}")
            
            # Validate against schema
            jsonschema.validate(response_json, self.OUTPUT_SCHEMA)
            
            # Convert to dataclass
            spans = [
                EvidenceSpan(
                    quote=span["quote"],
                    char_start=span["char_start"],
                    char_end=span["char_end"]
                )
                for span in response_json["spans"]
            ]
            
            return ClassificationOutput(
                label=response_json["label"],
                rationale=response_json["rationale"],
                spans=spans,
                safety=response_json["safety"]
            )
            
        except Exception as e:
            # Fallback to UNCLEAR on any error
            return ClassificationOutput(
                label="UNCLEAR",
                rationale=f"Classification failed due to error: {str(e)}",
                spans=[],
                safety={
                    "used_asr_confidence_rule": False,
                    "notes": f"Error during classification: {str(e)}"
                }
            )
    
    def classify_batch(self, inputs: List[ClassificationInput]) -> List[ClassificationOutput]:
        """Classify multiple segments."""
        return [self.classify(input_data) for input_data in inputs]


def main():
    """Example usage of the classifier."""
    # Initialize classifier
    classifier = HateSpeechClassifier()
    
    # Example input
    test_input = ClassificationInput(
        segment_text="This app is freaking useless. What a dumb idea.",
        segment_start=12.3,
        segment_end=17.8,
        asr_mean_confidence=0.86,
        confidence_threshold=0.45
    )
    
    # Classify
    result = classifier.classify(test_input)
    
    # Print results
    print("Classification Result:")
    print(f"Label: {result.label}")
    print(f"Rationale: {result.rationale}")
    print(f"Evidence spans: {len(result.spans)}")
    for span in result.spans:
        print(f"  - '{span.quote}' ({span.char_start}:{span.char_end})")
    print(f"Safety: {result.safety}")


if __name__ == "__main__":
    main()