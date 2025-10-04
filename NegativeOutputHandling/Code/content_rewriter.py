"""
Content rewriting functionality for removing offensive language.
"""

from abc import ABC, abstractmethod


class ContentRewriter(ABC):
    @abstractmethod
    async def rewrite_offensive_text(self, text: str, context: str) -> str:
        pass


class GroqContentRewriter(ContentRewriter):
    def __init__(self, api_key: str):
        from groq import Groq
        self.client = Groq(api_key=api_key)
    
    async def rewrite_offensive_text(self, text: str, context: str) -> str:
        # Use simple, direct replacements for common offensive language
        simple_replacements = {
            # Longer phrases first (to avoid partial matches)
            "didn't give a shit": "didn't care",
            "don't give a damn": "don't care", 
            "get our shit together": "get organized",
            "fucking around": "wasting time",
            "like they're on crack": "very erratically",
            "completely fucked": "completely broken",
            "total clusterfuck": "total mess",
            "shit-tier garbage": "terrible quality",
            "absolute garbage": "poor quality",
            "what a fucking joke": "disappointing",
            "tired of this crap": "tired of this nonsense",
            "go down the toilet": "go down the drain",
            "embarrassing as hell": "totally humiliating",
            "driving me crazy": "driving me nuts",
            "this is bullshit": "this is nonsense",
            "all over the fucking place": "completely disorganized",
            "fucking place": "place",
            "half-assed": "half-hearted",
            "screw this": "forget about it",
            "damn minds": "minds",
            
            # Single words (shorter phrases)
            "shitty": "terrible", 
            "shit": "poor",
            "crap": "junk", 
            "garbage": "trash",
            "fucking": "really",
            "fucked": "broken",
            "fuck": "mess",
            "bullshit": "nonsense",
            "clusterfuck": "clustermess",
            "damn": "very",
        }
        
        # Check for simple replacement first - find the longest match
        text_lower = text.lower().strip()
        best_match = None
        best_length = 0
        
        for offensive, replacement in simple_replacements.items():
            if offensive in text_lower and len(offensive) > best_length:
                best_match = (offensive, replacement)
                best_length = len(offensive)
        
        if best_match:
            offensive, replacement = best_match
            result = self._replace_preserving_case(text, offensive, replacement)
            return result
        
        # For complex cases, use AI with very strict prompting
        system_msg = """You are a professional language filter. Replace offensive language with appropriate alternatives while maintaining the same meaning and tone. Output ONLY the clean replacement text - no explanations, examples, or formatting."""
        
        user_msg = f"Clean this text: {text}"
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=max(20, len(text.split()) + 5),
                temperature=0.0
            )
            
            rewritten = response.choices[0].message.content.strip()
            
            # Aggressive cleanup of AI artifacts
            rewritten = self._clean_ai_artifacts(rewritten)
            
            # Fallback: if AI output is problematic, use simple word replacement
            if self._is_problematic_output(rewritten, text):
                return self._fallback_replacement(text)
                
            return rewritten
            
        except Exception as e:
            print(f"AI rewriting failed: {e}")
            return self._fallback_replacement(text)
    
    def _replace_preserving_case(self, text: str, offensive: str, replacement: str) -> str:
        """Replace offensive text while preserving original capitalization pattern."""
        import re
        
        # Find the offensive text with case-insensitive search
        pattern = re.escape(offensive)
        match = re.search(pattern, text, re.IGNORECASE)
        
        if not match:
            return text
            
        original = match.group()
        
        # Preserve capitalization pattern
        if original.isupper():
            replacement = replacement.upper()
        elif original.istitle():
            replacement = replacement.capitalize()
        elif original[0].isupper():
            replacement = replacement.capitalize()
            
        return text[:match.start()] + replacement + text[match.end():]
    
    def _clean_ai_artifacts(self, text: str) -> str:
        """Remove common AI artifacts and formatting issues."""
        import re
        
        # Remove quotes
        text = text.strip('"\'')
        
        # Remove arrows and example formatting
        text = re.sub(r'.*?→.*?', '', text)
        text = re.sub(r'.*?->.*?', '', text)
        text = re.sub(r'Example:.*', '', text)
        text = re.sub(r'Output:.*', '', text)
        text = re.sub(r'Clean version:.*', '', text)
        
        # Remove bullet points and numbering
        text = re.sub(r'^[-*•]\s*', '', text)
        text = re.sub(r'^\d+\.\s*', '', text)
        
        # Clean up multiple sentences - keep only the first meaningful one
        sentences = text.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 0:
                text = first_sentence
                if not text.endswith('.') and len(sentences) > 1:
                    text += '.'
        
        return text.strip()
    
    def _is_problematic_output(self, rewritten: str, original: str) -> bool:
        """Check if AI output has issues that require fallback."""
        if not rewritten or len(rewritten.strip()) == 0:
            return True
        if len(rewritten) > len(original) * 3:  # Too verbose
            return True
        if '"' in rewritten or "'" in rewritten:  # Still has quotes
            return True
        if '→' in rewritten or '->' in rewritten:  # Still has arrows
            return True
        return False
    
    def _fallback_replacement(self, text: str) -> str:
        """Simple word-by-word replacement as fallback."""
        fallback_map = {
            'shit': 'poor', 'fucking': 'really', 'fuck': 'mess', 
            'damn': 'very', 'crap': 'junk', 'bullshit': 'nonsense'
        }
        
        result = text
        for bad, good in fallback_map.items():
            # Simple case-insensitive replacement
            import re
            pattern = re.compile(re.escape(bad), re.IGNORECASE)
            result = pattern.sub(good, result)
        
        return result