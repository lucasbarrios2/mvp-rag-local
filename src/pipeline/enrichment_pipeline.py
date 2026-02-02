"""
Pipeline de Enriquecimento - MVP RAG Local
Processa clips do PostgreSQL e enriquece com análise multimodal
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, List
import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Imports internos (assumindo estrutura do projeto)
from config import settings
from models import VideoClip, AnalysisResult, EnrichmentResult

console = Console()


# ============================================================================
# FRAME EXTRACTOR
# ============================================================================

class FrameExtractor:
    """Extrai frames-chave de vídeos"""

    def __init__(self, cache_dir: Path = settings.frames_cache_path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, video_path: str, num_frames: int = None) -> List:
        """
        Extrai frames uniformemente distribuídos

        Returns:
            Lista de PIL Images
        """
        import cv2
        from PIL import Image

        num_frames = num_frames or settings.max_frames_per_clip

        # Verificar cache
        cache_key = self._get_cache_key(video_path)
        cached_frames = self._load_cache(cache_key)
        if cached_frames:
            return cached_frames

        # Extrair frames
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Não foi possível abrir vídeo: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            raise ValueError(f"Vídeo vazio: {video_path}")

        # Frames uniformemente distribuídos
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

        frames = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # BGR -> RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                frames.append(pil_img)

        cap.release()

        # Salvar no cache
        self._save_cache(cache_key, frames)

        return frames

    def get_duration(self, video_path: str) -> float:
        """Retorna duração do vídeo em segundos"""
        import cv2

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()

        if fps > 0:
            return frame_count / fps
        return 0.0

    def _get_cache_key(self, video_path: str) -> str:
        """Gera chave de cache baseada no path"""
        return hashlib.md5(video_path.encode()).hexdigest()

    def _load_cache(self, cache_key: str) -> Optional[List]:
        """Carrega frames do cache"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            import pickle
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_cache(self, cache_key: str, frames: List):
        """Salva frames no cache"""
        import pickle
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(frames, f)


# ============================================================================
# CLAUDE ANALYZER
# ============================================================================

class ClaudeAnalyzer:
    """Analisa clips com Claude 3.5 Sonnet"""

    ANALYSIS_PROMPT = """
Você é um especialista em análise de vídeos para canais de compilação no YouTube.

Analise este clip de vídeo (representado pelos frames-chave) e extraia as informações a seguir.

IMPORTANTE: Responda APENAS com JSON válido, sem markdown ou explicações adicionais.

{
  "scene_description": "Descrição objetiva em 2-3 frases do que acontece visualmente",

  "visual_elements": [
    "lista de elementos visuais importantes: pessoas, objetos, cenário, etc"
  ],

  "key_moments": [
    {"timestamp": 0.0, "event": "início/setup"},
    {"timestamp": 0.5, "event": "desenvolvimento"},
    {"timestamp": 1.0, "event": "clímax/payoff"}
  ],

  "emotional_tone": "escolha UMA: cômico | épico | emocionante | tenso | wholesome | absurdo",

  "intensity": 7.5,
  "surprise_factor": 8.0,
  "viral_potential": 7.0,

  "narrative_arc": "ex: setup -> escalation -> payoff",

  "standalone": true,

  "theme_scores": {
    "fails_accidents": 9.0,
    "extreme_sports": 7.0,
    "comedy": 8.0,
    "wholesome_moments": 2.0,
    "instant_regret": 9.0,
    "tutorial_fail": 3.0,
    "animal_antics": 0.0,
    "epic_wins": 2.0
  }
}

ESCALAS (todas 0-10):
- intensity: Quão intensa/energética é a cena
- surprise_factor: Elemento de surpresa/inesperado
- viral_potential: Potencial de compartilhamento/viralização
- theme_scores: Adequação para cada tema (0-10)

Analise agora:
"""

    def __init__(self, api_key: str = settings.anthropic_api_key):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze(self, frames: List) -> AnalysisResult:
        """
        Analisa frames e retorna análise estruturada

        Args:
            frames: Lista de PIL Images

        Returns:
            AnalysisResult
        """
        import base64
        from io import BytesIO

        # Preparar frames
        frame_contents = []
        for frame in frames[:settings.max_frames_per_clip]:
            buffered = BytesIO()
            # Resize se necessário
            if frame.size[0] > 1024:
                frame.thumbnail((1024, 1024))
            frame.save(buffered, format="JPEG")
            b64_data = base64.b64encode(buffered.getvalue()).decode()

            frame_contents.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64_data
                }
            })

        # Adicionar prompt
        frame_contents.append({
            "type": "text",
            "text": self.ANALYSIS_PROMPT
        })

        # Chamar Claude
        response = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
            messages=[{
                "role": "user",
                "content": frame_contents
            }]
        )

        # Parse JSON
        response_text = response.content[0].text

        # Limpar markdown se houver
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        data = json.loads(response_text)

        # Converter para AnalysisResult
        return AnalysisResult(**data)


# ============================================================================
# EMBEDDING GENERATOR
# ============================================================================

class EmbeddingGenerator:
    """Gera embeddings com CLIP"""

    def __init__(self):
        from transformers import CLIPModel, CLIPProcessor
        import torch

        self.device = self._get_device()
        self.model = CLIPModel.from_pretrained(settings.clip_model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(settings.clip_model_name)

    def _get_device(self) -> str:
        """Detecta dispositivo disponível"""
        import torch

        if settings.clip_device != "auto":
            return settings.clip_device

        return "cuda" if torch.cuda.is_available() else "cpu"

    def generate(self, frames: List, description: str = None) -> np.ndarray:
        """
        Gera embedding multimodal

        Args:
            frames: Lista de PIL Images
            description: Descrição textual (opcional)

        Returns:
            numpy array [768] para ViT-L/14
        """
        import torch

        # Embedding de imagens
        inputs = self.processor(images=frames, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            img_features = self.model.get_image_features(**inputs)

        # Average pooling
        img_emb = img_features.mean(dim=0)

        # Se tiver descrição, combinar
        if description:
            txt_inputs = self.processor(text=[description], return_tensors="pt")
            txt_inputs = {k: v.to(self.device) for k, v in txt_inputs.items()}

            with torch.no_grad():
                txt_features = self.model.get_text_features(**txt_inputs)

            txt_emb = txt_features[0]

            # Fusão 70% visual + 30% textual
            combined = 0.7 * img_emb + 0.3 * txt_emb
            combined = combined / combined.norm()
            return combined.cpu().numpy()

        # Apenas visual
        img_emb = img_emb / img_emb.norm()
        return img_emb.cpu().numpy()


# ============================================================================
# QDRANT CLIENT
# ============================================================================

class QdrantIndexer:
    """Cliente Qdrant para indexar embeddings"""

    def __init__(self):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        self.collection_name = settings.qdrant_collection_name
        self._ensure_collection()

    def _ensure_collection(self):
        """Cria collection se não existir"""
        from qdrant_client.models import Distance, VectorParams

        collections = [c.name for c in self.client.get_collections().collections]

        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.qdrant_vector_size,
                    distance=Distance.COSINE
                )
            )

    def index(self, clip_id: int, embedding: np.ndarray, payload: dict):
        """Indexa clip no Qdrant"""
        from qdrant_client.models import PointStruct

        point = PointStruct(
            id=str(clip_id),  # Qdrant usa string IDs
            vector=embedding.tolist(),
            payload=payload
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )


# ============================================================================
# ENRICHMENT PIPELINE
# ============================================================================

class EnrichmentPipeline:
    """Pipeline completo de enriquecimento"""

    def __init__(self):
        self.frame_extractor = FrameExtractor()
        self.claude_analyzer = ClaudeAnalyzer()
        self.embedding_generator = EmbeddingGenerator()
        self.qdrant_indexer = QdrantIndexer()

        # Database
        engine = create_engine(settings.postgres_url)
        self.SessionLocal = sessionmaker(bind=engine)

    def enrich_clip(self, clip_id: int, force: bool = False) -> EnrichmentResult:
        """
        Enriquece um único clip

        Args:
            clip_id: ID do clip no PostgreSQL
            force: Re-analisar mesmo se já foi processado

        Returns:
            EnrichmentResult
        """
        start_time = time.time()

        session = self.SessionLocal()

        try:
            # Buscar clip
            clip = session.query(VideoClip).filter_by(id=clip_id).first()
            if not clip:
                return EnrichmentResult(
                    success=False,
                    clip_id=clip_id,
                    id_origem="",
                    error="Clip não encontrado"
                )

            # Verificar se já foi processado
            if clip.processing_status == "analyzed" and not force:
                return EnrichmentResult(
                    success=True,
                    clip_id=clip_id,
                    id_origem=clip.id_origem or "",
                    error="Já foi analisado (use force=True para re-analisar)"
                )

            # Atualizar status
            clip.processing_status = "analyzing"
            session.commit()

            # 1. Extrair frames
            video_path = clip.local
            frames = self.frame_extractor.extract(video_path)

            # Obter duração
            if not clip.duration_seconds:
                clip.duration_seconds = self.frame_extractor.get_duration(video_path)

            # 2. Analisar com Claude
            analysis = self.claude_analyzer.analyze(frames)

            # 3. Gerar embedding
            embedding = self.embedding_generator.generate(
                frames,
                description=analysis.scene_description
            )

            # 4. Atualizar PostgreSQL
            clip.scene_description = analysis.scene_description
            clip.visual_elements = analysis.visual_elements
            clip.key_moments = analysis.key_moments
            clip.emotional_tone = analysis.emotional_tone
            clip.intensity = analysis.intensity
            clip.surprise_factor = analysis.surprise_factor
            clip.viral_potential = analysis.viral_potential
            clip.narrative_arc = analysis.narrative_arc
            clip.standalone = analysis.standalone
            clip.theme_scores = analysis.theme_scores
            clip.embedding_id = str(clip_id)
            clip.processing_status = "analyzed"
            clip.last_analyzed_at = func.now()

            session.commit()

            # 5. Indexar no Qdrant
            payload = {
                "id_origem": clip.id_origem,
                "descricao_breve": clip.descricao_breve,
                "scene_description": analysis.scene_description,
                "emotional_tone": analysis.emotional_tone,
                "intensity": analysis.intensity,
                "viral_potential": analysis.viral_potential,
                "categorias": clip.categorias or [],
                "tags": clip.tags or []
            }

            self.qdrant_indexer.index(clip_id, embedding, payload)

            processing_time = time.time() - start_time

            return EnrichmentResult(
                success=True,
                clip_id=clip_id,
                id_origem=clip.id_origem or "",
                analysis=analysis,
                embedding_generated=True,
                processing_time_seconds=processing_time
            )

        except Exception as e:
            # Marcar como falho
            if clip:
                clip.processing_status = "failed"
                session.commit()

            return EnrichmentResult(
                success=False,
                clip_id=clip_id,
                id_origem=clip.id_origem if clip else "",
                error=str(e),
                processing_time_seconds=time.time() - start_time
            )

        finally:
            session.close()

    def enrich_batch(self, limit: int = None, force: bool = False) -> List[EnrichmentResult]:
        """
        Enriquece clips em lote

        Args:
            limit: Número de clips para processar (None = todos pendentes)
            force: Re-processar clips já analisados

        Returns:
            Lista de EnrichmentResult
        """
        session = self.SessionLocal()

        # Buscar clips pendentes
        query = session.query(VideoClip)

        if not force:
            query = query.filter_by(processing_status="pending")

        if limit:
            query = query.limit(limit)

        clips = query.all()
        session.close()

        if not clips:
            console.print("[yellow]Nenhum clip pendente de análise[/yellow]")
            return []

        # Processar com progress bar
        results = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Processando {len(clips)} clips...",
                total=len(clips)
            )

            for clip in clips:
                result = self.enrich_clip(clip.id, force=force)
                results.append(result)

                # Log
                if result.success:
                    console.print(
                        f"[green]✓[/green] {clip.id_origem}: "
                        f"{result.analysis.emotional_tone}, "
                        f"viral={result.analysis.viral_potential:.1f}"
                    )
                else:
                    console.print(f"[red]✗[/red] {clip.id_origem}: {result.error}")

                progress.advance(task)

        return results


# ============================================================================
# MAIN (para testes)
# ============================================================================

if __name__ == "__main__":
    pipeline = EnrichmentPipeline()

    # Enriquecer primeiros 5 clips
    console.print("\n[bold cyan]🎬 Iniciando Pipeline de Enriquecimento[/bold cyan]\n")

    results = pipeline.enrich_batch(limit=5)

    # Resumo
    console.print("\n[bold]📊 Resumo:[/bold]")
    console.print(f"  Processados: {len(results)}")
    console.print(f"  Sucesso: {sum(1 for r in results if r.success)}")
    console.print(f"  Falhas: {sum(1 for r in results if not r.success)}")
