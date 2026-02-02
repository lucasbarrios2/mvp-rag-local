"""
EmbeddingService - Geracao de embeddings de texto via Google API.
"""

from google import genai

from src.models import VideoAnalysis


class EmbeddingService:
    def __init__(self, api_key: str, model: str, dimensions: int):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    def generate(self, text: str) -> list[float]:
        """Gera embedding de texto via Google API."""
        result = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config={
                "output_dimensionality": self.dimensions,
            },
        )
        return result.embeddings[0].values

    def generate_for_video(self, analysis: VideoAnalysis) -> list[float]:
        """Combina campos da analise em texto rico e gera embedding."""
        parts = [analysis.description]

        if analysis.tags:
            parts.append("Tags: " + ", ".join(analysis.tags))

        if analysis.emotional_tone:
            parts.append(f"Tom emocional: {analysis.emotional_tone}")

        if analysis.themes:
            themes_str = ", ".join(
                f"{k} ({v})" for k, v in analysis.themes.items()
            )
            parts.append(f"Temas: {themes_str}")

        if analysis.key_moments:
            moments = [m.get("event", "") for m in analysis.key_moments if m.get("event")]
            if moments:
                parts.append("Momentos: " + "; ".join(moments))

        combined_text = ". ".join(parts)
        return self.generate(combined_text)
