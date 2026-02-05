"""
GeminiService - Analise de video e geracao de respostas RAG via Google Gemini.
"""

import json
import time

from google import genai
from google.genai import types

from src.models import VideoAnalysis, DualVideoAnalysis


# ============================================================================
# PROMPTS DE ANÁLISE VISUAL (foco em elementos visuais frame a frame)
# ============================================================================

VISUAL_ANALYSIS_PROMPT = """Analise este video VISUALMENTE, frame a frame, focando nos elementos visuais.
Retorne um JSON com a seguinte estrutura:

{
  "visual_description": "Descricao detalhada dos elementos VISUAIS: objetos, pessoas, cenarios, cores, movimentos, composicao, iluminacao, transicoes visuais (3-5 frases)",
  "visual_tags": ["tag1", "tag2", ...],
  "objects_detected": ["objeto1", "objeto2", ...],
  "scenes": [
    {"timestamp_ms": 0, "scene_description": "descricao visual da cena"},
    {"timestamp_ms": 2500, "scene_description": "descricao visual da cena"}
  ],
  "visual_style": "estilo visual predominante (ex: cinematografico, amador, animacao, documental, artistico)",
  "color_palette": ["cor1", "cor2", ...],
  "movement_intensity": 7.5,
  "duration_estimate": 15.0
}

Instrucoes:
- visual_description: Descreva O QUE VOCE VE no video, nao interprete significados
- visual_tags: 15-20 tags de elementos VISUAIS (objetos, acoes, cenarios, cores)
- objects_detected: Liste todos os objetos e elementos visiveis
- scenes: Descreva visualmente cada cena/corte do video com timestamps
- color_palette: Cores predominantes no video
- movement_intensity: de 0 (estatico) a 10 (muito movimento)

Retorne APENAS o JSON, sem markdown, sem ```json, sem explicacao adicional."""


# ============================================================================
# PROMPTS DE ANÁLISE NARRATIVA (foco em contexto e significado)
# ============================================================================

NARRATIVE_ANALYSIS_PROMPT = """Analise este video do ponto de vista NARRATIVO e CONTEXTUAL.
Retorne um JSON com a seguinte estrutura:

{
  "narrative_description": "Descricao da NARRATIVA e MENSAGEM do video: o que esta acontecendo, qual a historia sendo contada, qual o contexto (3-5 frases)",
  "narrative_tags": ["tag1", "tag2", ...],
  "emotional_tone": "tom emocional predominante (ex: comico, epico, wholesome, tenso, absurdo, emocionante, calmo, inspirador, melancolico, energetico)",
  "themes": {"tema1": 8.0, "tema2": 6.5},
  "storytelling_elements": {
    "has_narrative_arc": true,
    "has_conflict": false,
    "has_resolution": true,
    "pacing": "rapido"
  },
  "target_audience": "descricao do publico-alvo provavel",
  "viral_potential": 8.0,
  "intensity": 7.5,
  "key_moments": [
    {"timestamp_ms": 0, "event": "descricao do momento narrativo"},
    {"timestamp_ms": 2500, "event": "descricao do momento narrativo"}
  ]
}

Instrucoes:
- narrative_description: Interprete O SIGNIFICADO e CONTEXTO do video
- narrative_tags: 15-20 tags de conceitos, emocoes, temas, mensagens
- emotional_tone: Tom emocional predominante
- themes: scores de 0 a 10 para temas como: humor, drama, romance, acao, suspense, educacao, etc
- intensity: de 0 (calmo) a 10 (intenso)
- viral_potential: de 0 (sem potencial) a 10 (altamente viral)

Retorne APENAS o JSON, sem markdown, sem ```json, sem explicacao adicional."""


RAG_PROMPT_TEMPLATE = """Voce e um curador de videos inteligente. O usuario fez a seguinte busca:

"{query}"

Encontrei os seguintes videos relevantes no acervo:

{clips_context}

Com base na busca do usuario e nos videos encontrados, gere uma resposta explicando:
1. Por que cada video e relevante para a busca
2. Destaque os aspectos mais interessantes de cada video
3. Sugira uma ordem de visualizacao se fizer sentido

Seja conciso e direto. Responda em portugues."""


RAG_VIDEO_PROMPT_TEMPLATE = """Voce e um curador de videos inteligente. O usuario fez a seguinte busca:

"{query}"

Estou enviando {num_videos} video(s) para voce analisar diretamente. Os videos estao ordenados por relevancia (primeiro = mais relevante).

Assista cada video com atencao e responda:
1. Descreva brevemente o que acontece em cada video
2. Explique por que cada video e relevante (ou nao) para a busca do usuario
3. Destaque momentos especificos interessantes (com timestamps aproximados se possivel)
4. Sugira qual video melhor atende a busca e por que

Seja detalhado mas objetivo. Responda em portugues."""


class GeminiService:
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        # Modelo rapido para RAG com video (evita timeout)
        self.fast_model = "gemini-2.0-flash"

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON da resposta do Gemini, removendo markdown se necessario."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)

    def _upload_and_wait(self, video_path: str, timeout: int = 300) -> object:
        """Upload video para File API e aguarda processamento."""
        video_file = self.client.files.upload(file=video_path)

        start_time = time.time()
        while video_file.state == "PROCESSING":
            if time.time() - start_time > timeout:
                raise RuntimeError("Timeout no processamento do video")
            time.sleep(2)
            video_file = self.client.files.get(name=video_file.name)

        if video_file.state == "FAILED":
            raise RuntimeError(f"Falha no processamento do video: {video_file.state}")

        return video_file

    def analyze_video_dual(self, video_path: str) -> DualVideoAnalysis:
        """
        Upload video para Gemini e executa DUAS analises (visual + narrativa).
        Usa um unico upload para ambas as analises (eficiente).
        """
        from src.models import VisualAnalysis, NarrativeAnalysis, DualVideoAnalysis

        # 1. Upload via File API (uma unica vez)
        video_file = self._upload_and_wait(video_path)

        try:
            video_part = types.Part.from_uri(
                file_uri=video_file.uri,
                mime_type=video_file.mime_type,
            )

            # 2. Analise VISUAL (frame a frame)
            visual_response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[video_part, types.Part.from_text(text=VISUAL_ANALYSIS_PROMPT)],
                    )
                ],
            )
            visual_data = self._parse_json_response(visual_response.text)
            visual_analysis = VisualAnalysis(**visual_data)

            # 3. Analise NARRATIVA (contexto e significado)
            narrative_response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[video_part, types.Part.from_text(text=NARRATIVE_ANALYSIS_PROMPT)],
                    )
                ],
            )
            narrative_data = self._parse_json_response(narrative_response.text)
            narrative_analysis = NarrativeAnalysis(**narrative_data)

            return DualVideoAnalysis(visual=visual_analysis, narrative=narrative_analysis)

        finally:
            # 4. Cleanup - deletar arquivo da API
            try:
                self.client.files.delete(name=video_file.name)
            except Exception:
                pass

    def analyze_video(self, video_path: str) -> VideoAnalysis:
        """
        Metodo legado - converte DualVideoAnalysis para VideoAnalysis.
        Mantido para compatibilidade com codigo existente.
        """
        dual = self.analyze_video_dual(video_path)

        # Combinar as duas analises no formato antigo
        combined_description = (
            f"[VISUAL] {dual.visual.visual_description}\n\n"
            f"[NARRATIVA] {dual.narrative.narrative_description}"
        )
        combined_tags = list(set(dual.visual.visual_tags + dual.narrative.narrative_tags))

        return VideoAnalysis(
            description=combined_description,
            tags=combined_tags,
            emotional_tone=dual.narrative.emotional_tone,
            intensity=dual.narrative.intensity,
            viral_potential=dual.narrative.viral_potential,
            key_moments=dual.narrative.key_moments,
            themes=dual.narrative.themes,
            duration_estimate=dual.visual.duration_estimate,
        )

    def generate_rag_response(
        self, query: str, clips_context: list[dict]
    ) -> str:
        """Gera resposta RAG com contexto dos videos encontrados."""

        context_text = ""
        for i, clip in enumerate(clips_context, 1):
            context_text += f"\n--- Video {i}: {clip.get('filename', 'N/A')} ---\n"
            context_text += f"Descricao: {clip.get('analysis_description', 'N/A')}\n"
            context_text += f"Tags: {', '.join(clip.get('tags', []))}\n"
            context_text += f"Tom emocional: {clip.get('emotional_tone', 'N/A')}\n"
            context_text += f"Intensidade: {clip.get('intensity', 'N/A')}/10\n"
            context_text += f"Potencial viral: {clip.get('viral_potential', 'N/A')}/10\n"
            themes = clip.get("themes", {})
            if themes:
                themes_str = ", ".join(
                    f"{k}: {v}" for k, v in themes.items()
                )
                context_text += f"Temas: {themes_str}\n"
            context_text += f"Relevancia (score): {clip.get('score', 'N/A')}\n"

        prompt = RAG_PROMPT_TEMPLATE.format(
            query=query, clips_context=context_text
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text

    def generate_rag_response_with_videos(
        self,
        query: str,
        video_paths: list[str],
        max_videos: int = 3,
        timeout_per_video: int = 120,
    ) -> str:
        """
        Gera resposta RAG enviando os videos diretamente para o Gemini.

        Args:
            query: Busca do usuario
            video_paths: Lista de caminhos dos videos (ordenados por relevancia)
            max_videos: Maximo de videos a enviar (default 3 para evitar timeout)
            timeout_per_video: Timeout em segundos para processar cada video

        Returns:
            Resposta do Gemini baseada na analise dos videos
        """
        # Limitar quantidade de videos
        paths_to_process = video_paths[:max_videos]

        if not paths_to_process:
            return "Nenhum video disponivel para analise."

        uploaded_files = []
        failed_uploads = []

        try:
            # 1. Upload de todos os videos com timeout
            for path in paths_to_process:
                try:
                    video_file = self.client.files.upload(file=path)

                    # Aguardar processamento com timeout
                    start_time = time.time()
                    while video_file.state == "PROCESSING":
                        elapsed = time.time() - start_time
                        if elapsed > timeout_per_video:
                            failed_uploads.append(f"{path} (timeout)")
                            break
                        time.sleep(3)
                        video_file = self.client.files.get(name=video_file.name)

                    if video_file.state == "FAILED":
                        failed_uploads.append(f"{path} (falha no processamento)")
                        continue

                    if video_file.state == "ACTIVE":
                        uploaded_files.append(video_file)

                except Exception as e:
                    failed_uploads.append(f"{path} ({str(e)[:50]})")
                    continue

            if not uploaded_files:
                error_details = "; ".join(failed_uploads) if failed_uploads else "erro desconhecido"
                return f"Nao foi possivel processar os videos para analise. Erros: {error_details}"

            # 2. Montar conteudo multimodal
            parts = []

            # Adicionar cada video
            for video_file in uploaded_files:
                parts.append(
                    types.Part.from_uri(
                        file_uri=video_file.uri,
                        mime_type=video_file.mime_type,
                    )
                )

            # Adicionar prompt
            prompt = RAG_VIDEO_PROMPT_TEMPLATE.format(
                query=query,
                num_videos=len(uploaded_files),
            )
            parts.append(types.Part.from_text(text=prompt))

            # 3. Gerar resposta (usa modelo rapido para evitar timeout)
            response = self.client.models.generate_content(
                model=self.fast_model,
                contents=[
                    types.Content(role="user", parts=parts)
                ],
            )

            result = response.text

            # Adicionar nota se alguns videos falharam
            if failed_uploads:
                result += f"\n\n_Nota: {len(failed_uploads)} video(s) nao puderam ser analisados._"

            return result

        except Exception as e:
            return f"Erro ao gerar resposta com videos: {str(e)}"

        finally:
            # 4. Cleanup - deletar arquivos da API
            for video_file in uploaded_files:
                try:
                    self.client.files.delete(name=video_file.name)
                except Exception:
                    pass
