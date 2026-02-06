"""
ContextComposer - Compoe texto rico de todas as camadas de um video para embedding unificado.
"""

from typing import Optional

from src.compilation_themes import COMPILATION_THEMES


class ContextComposer:
    """
    Compoe texto rico combinando todas as camadas de contexto de um video:
    source metadata, visual analysis, narrative analysis, audio context.
    """

    def compose_embedding_text(self, video) -> str:
        """
        Junta todas as camadas de contexto num texto rico para embedding.

        Args:
            video: Instancia do Video ORM com todos os campos

        Returns:
            Texto combinado para gerar embedding unificado
        """
        parts = []

        # Camada 1: Source metadata (Newsflare / MENTOR)
        if video.source_description:
            parts.append(video.source_description)
        if video.category:
            parts.append(f"Categoria: {video.category}")
        if video.filming_location:
            parts.append(f"Local: {video.filming_location}")
        if video.source_tags:
            tags = video.source_tags if isinstance(video.source_tags, list) else []
            if tags:
                parts.append("Tags fonte: " + ", ".join(tags))

        # Camada 2: Visual analysis
        if video.visual_description:
            parts.append(video.visual_description)
        if video.visual_tags:
            tags = video.visual_tags if isinstance(video.visual_tags, list) else []
            if tags:
                parts.append("Elementos visuais: " + ", ".join(tags))
        if video.objects_detected:
            objs = video.objects_detected if isinstance(video.objects_detected, list) else []
            if objs:
                parts.append("Objetos: " + ", ".join(objs))
        if video.visual_style:
            parts.append(f"Estilo: {video.visual_style}")
        if video.scenes:
            scenes = video.scenes if isinstance(video.scenes, list) else []
            scene_descriptions = [
                s.get("scene_description", "") for s in scenes if s.get("scene_description")
            ]
            if scene_descriptions:
                parts.append("Cenas: " + "; ".join(scene_descriptions))

        # Camada 3: Narrative analysis
        if video.narrative_description:
            parts.append(video.narrative_description)
        if video.narrative_tags:
            tags = video.narrative_tags if isinstance(video.narrative_tags, list) else []
            if tags:
                parts.append("Conceitos: " + ", ".join(tags))
        if video.emotional_tone:
            parts.append(f"Tom emocional: {video.emotional_tone}")
        if video.themes:
            themes = video.themes if isinstance(video.themes, dict) else {}
            if themes:
                themes_str = ", ".join(f"{k} ({v})" for k, v in themes.items())
                parts.append(f"Temas: {themes_str}")
        if video.target_audience:
            parts.append(f"Publico: {video.target_audience}")
        if video.key_moments:
            moments = video.key_moments if isinstance(video.key_moments, list) else []
            events = [m.get("event", "") for m in moments if m.get("event")]
            if events:
                parts.append("Momentos: " + "; ".join(events))

        # Camada 4: Audio context
        if video.audio_description:
            parts.append(video.audio_description)
        if video.audio_transcript:
            parts.append(f"Transcricao: {video.audio_transcript[:500]}")

        # Camada 5: Compilation analysis
        if getattr(video, "event_headline", None):
            parts.append(f"Headline: {video.event_headline}")
        if getattr(video, "compilation_themes", None):
            themes_list = video.compilation_themes if isinstance(video.compilation_themes, list) else []
            resolved = [COMPILATION_THEMES.get(t, t) for t in themes_list]
            if resolved:
                parts.append("Temas compilacao: " + ", ".join(resolved))
        if getattr(video, "camera_type", None):
            parts.append(f"Camera: {video.camera_type}")
        if getattr(video, "location_country", None):
            parts.append(f"Pais: {video.location_country}")
        if getattr(video, "location_environment", None):
            parts.append(f"Ambiente: {video.location_environment}")
        if getattr(video, "narration_suggestion", None):
            parts.append(f"Narracao: {video.narration_suggestion}")

        # Fallback: campos legados
        if not parts and video.analysis_description:
            parts.append(video.analysis_description)
            if video.tags:
                tags = video.tags if isinstance(video.tags, list) else []
                if tags:
                    parts.append("Tags: " + ", ".join(tags))

        return ". ".join(parts) if parts else ""

    def compose_rag_context(self, video, score: float = 0.0) -> dict:
        """
        Monta dict com todo o contexto disponivel para gerar resposta RAG.

        Args:
            video: Instancia do Video ORM
            score: Score de similaridade da busca

        Returns:
            Dict com contexto completo para RAG
        """
        context = {
            "video_id": video.id,
            "filename": video.filename,
            "score": score,
        }

        # Source metadata
        if video.category:
            context["category"] = video.category
        if video.filming_location:
            context["filming_location"] = video.filming_location
        if video.source_description:
            context["source_description"] = video.source_description
        if video.is_exclusive:
            context["is_exclusive"] = video.is_exclusive

        # Visual
        if video.visual_description:
            context["visual_description"] = video.visual_description
        if video.visual_tags:
            context["visual_tags"] = video.visual_tags

        # Narrative
        if video.narrative_description:
            context["narrative_description"] = video.narrative_description
        if video.emotional_tone:
            context["emotional_tone"] = video.emotional_tone
        if video.intensity is not None:
            context["intensity"] = video.intensity
        if video.viral_potential is not None:
            context["viral_potential"] = video.viral_potential
        if video.themes:
            context["themes"] = video.themes
        if video.key_moments:
            context["key_moments"] = video.key_moments
        if video.target_audience:
            context["target_audience"] = video.target_audience

        # Compilation
        if getattr(video, "event_headline", None):
            context["event_headline"] = video.event_headline
        if getattr(video, "trim_in_ms", None) is not None:
            context["trim_in_ms"] = video.trim_in_ms
        if getattr(video, "trim_out_ms", None) is not None:
            context["trim_out_ms"] = video.trim_out_ms
        if getattr(video, "money_shot_ms", None) is not None:
            context["money_shot_ms"] = video.money_shot_ms
        if getattr(video, "camera_type", None):
            context["camera_type"] = video.camera_type
        if getattr(video, "audio_usability", None):
            context["audio_usability"] = video.audio_usability
        if getattr(video, "audio_usability_reason", None):
            context["audio_usability_reason"] = video.audio_usability_reason
        if getattr(video, "compilation_themes", None):
            context["compilation_themes"] = video.compilation_themes
        if getattr(video, "narration_suggestion", None):
            context["narration_suggestion"] = video.narration_suggestion
        if getattr(video, "location_country", None):
            context["location_country"] = video.location_country
        if getattr(video, "location_environment", None):
            context["location_environment"] = video.location_environment
        if getattr(video, "standalone_score", None) is not None:
            context["standalone_score"] = video.standalone_score
        if getattr(video, "visual_quality_score", None) is not None:
            context["visual_quality_score"] = video.visual_quality_score

        # Legado fallback
        if video.analysis_description:
            context["analysis_description"] = video.analysis_description
        if video.tags:
            context["tags"] = video.tags

        # Audio
        if video.audio_description:
            context["audio_description"] = video.audio_description

        # File info
        if video.duration_seconds:
            context["duration_seconds"] = video.duration_seconds
        if video.file_path:
            context["file_path"] = video.file_path

        return context
