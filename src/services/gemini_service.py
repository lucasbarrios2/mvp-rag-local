"""
GeminiService - Analise de video e geracao de respostas RAG via Google Gemini.
"""

import json
import time

from google import genai
from google.genai import types

from src.models import VideoAnalysis


ANALYSIS_PROMPT = """Analise este video em detalhes e retorne um JSON com a seguinte estrutura exata:

{
  "description": "Descricao rica e detalhada do conteudo do video, incluindo cenario, acoes, pessoas e contexto (2-4 frases)",
  "tags": ["tag1", "tag2", ...],
  "emotional_tone": "tom emocional predominante (ex: comico, epico, wholesome, tenso, absurdo, emocionante, calmo, inspirador, melancolico, energetico)",
  "intensity": 7.5,
  "viral_potential": 8.0,
  "key_moments": [
    {"timestamp_ms": 0, "event": "descricao do momento"},
    {"timestamp_ms": 2500, "event": "descricao do momento"}
  ],
  "themes": {"tema1": 8.0, "tema2": 6.5},
  "duration_estimate": 15.0
}

Instrucoes:
- tags: 15-20 tags descritivas em portugues, incluindo acoes, objetos, cenarios, emocoes e conceitos
- intensity: de 0 (calmo) a 10 (extremamente intenso)
- viral_potential: de 0 (sem potencial) a 10 (altamente viral)
- key_moments: momentos-chave com timestamps em milissegundos
- themes: scores de 0 a 10 para temas como: humor, esporte, musica, natureza, tecnologia, arte, comida, viagem, educacao, entretenimento, etc (inclua apenas temas relevantes)
- duration_estimate: duracao estimada do video em segundos

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


class GeminiService:
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def analyze_video(self, video_path: str) -> VideoAnalysis:
        """Upload video para Gemini, analisa e retorna resultado estruturado."""

        # 1. Upload via File API
        video_file = self.client.files.upload(file=video_path)

        # 2. Aguardar processamento
        while video_file.state == "PROCESSING":
            time.sleep(2)
            video_file = self.client.files.get(name=video_file.name)

        if video_file.state == "FAILED":
            raise RuntimeError(
                f"Falha no processamento do video: {video_file.state}"
            )

        # 3. Gerar analise
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_uri(
                                file_uri=video_file.uri,
                                mime_type=video_file.mime_type,
                            ),
                            types.Part.from_text(text=ANALYSIS_PROMPT),
                        ],
                    )
                ],
            )
        finally:
            # 4. Cleanup - deletar arquivo da API
            try:
                self.client.files.delete(name=video_file.name)
            except Exception:
                pass

        # 5. Parse resposta
        text = response.text.strip()
        # Remover possivel markdown wrapping
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)
        return VideoAnalysis(**data)

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
