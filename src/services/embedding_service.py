"""
EmbeddingService - Geracao de embeddings de texto via Google API.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

from google import genai

from src.models import VideoAnalysis, DualVideoAnalysis, FullVideoAnalysis, VisualAnalysis, NarrativeAnalysis

logger = logging.getLogger(__name__)


@dataclass
class DualEmbeddings:
    """Embeddings duplos para busca visual e narrativa."""
    visual: list[float]
    narrative: list[float]


class EmbeddingService:
    def __init__(self, api_key: str, model: str, dimensions: int):
        self.client_v1 = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
        self.client_default = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    def _try_embed(self, client, model: str, text: str) -> list[float]:
        result = client.models.embed_content(
            model=model,
            contents=text,
            config={"output_dimensionality": self.dimensions},
        )
        return result.embeddings[0].values

    def generate(self, text: str) -> list[float]:
        """Gera embedding com retries em diferentes API versions."""
        attempts = [
            (self.client_default, self.model),
            (self.client_v1, self.model),
            (self.client_default, self.model),  # retry default
            (self.client_v1, self.model),        # retry v1
        ]
        last_error = None
        for i, (client, model) in enumerate(attempts):
            try:
                result = self._try_embed(client, model, text)
                if i > 0:
                    logger.info(f"Embedding succeeded on attempt {i + 1}")
                return result
            except Exception as e:
                last_error = e
                wait = min(2 ** i, 4)
                logger.warning(f"Embedding attempt {i + 1} failed ({model}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
        raise last_error

    def generate_unified(self, composed_text: str) -> list[float]:
        """Gera embedding unificado a partir de texto ja composto pelo ContextComposer."""
        return self.generate(composed_text)

    def generate_for_visual(self, analysis: VisualAnalysis) -> list[float]:
        """Gera embedding para analise VISUAL."""
        parts = [analysis.visual_description]

        if analysis.visual_tags:
            parts.append("Elementos visuais: " + ", ".join(analysis.visual_tags))

        if analysis.objects_detected:
            parts.append("Objetos: " + ", ".join(analysis.objects_detected))

        if analysis.visual_style:
            parts.append(f"Estilo: {analysis.visual_style}")

        if analysis.color_palette:
            parts.append("Cores: " + ", ".join(analysis.color_palette))

        if analysis.scenes:
            scene_descriptions = [s.get("scene_description", "") for s in analysis.scenes if s.get("scene_description")]
            if scene_descriptions:
                parts.append("Cenas: " + "; ".join(scene_descriptions))

        combined_text = ". ".join(parts)
        return self.generate(combined_text)

    def generate_for_narrative(self, analysis: NarrativeAnalysis) -> list[float]:
        """Gera embedding para analise NARRATIVA."""
        parts = [analysis.narrative_description]

        if analysis.narrative_tags:
            parts.append("Conceitos: " + ", ".join(analysis.narrative_tags))

        if analysis.emotional_tone:
            parts.append(f"Tom emocional: {analysis.emotional_tone}")

        if analysis.themes:
            themes_str = ", ".join(f"{k} ({v})" for k, v in analysis.themes.items())
            parts.append(f"Temas: {themes_str}")

        if analysis.target_audience:
            parts.append(f"Publico: {analysis.target_audience}")

        if analysis.key_moments:
            moments = [m.get("event", "") for m in analysis.key_moments if m.get("event")]
            if moments:
                parts.append("Momentos: " + "; ".join(moments))

        combined_text = ". ".join(parts)
        return self.generate(combined_text)

    def generate_dual(self, analysis: DualVideoAnalysis | FullVideoAnalysis) -> DualEmbeddings:
        """Gera embeddings para ambas as analises (visual + narrativa)."""
        visual_embedding = self.generate_for_visual(analysis.visual)
        narrative_embedding = self.generate_for_narrative(analysis.narrative)
        return DualEmbeddings(visual=visual_embedding, narrative=narrative_embedding)

    def generate_for_video(self, analysis: VideoAnalysis) -> list[float]:
        """Metodo legado - combina campos da analise em texto rico e gera embedding."""
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
