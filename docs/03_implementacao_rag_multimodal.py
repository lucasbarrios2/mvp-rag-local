"""
Sistema RAG Multimodal para Curadoria de Vídeos
Janeiro 2026 - Implementação de Produção

Dependências:
    pip install anthropic openai qdrant-client transformers torch \
                opencv-python scenedetect pillow psycopg2-binary \
                sentence-transformers imagehash numpy
"""

import os
import json
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from datetime import datetime

# AI Models
import anthropic
from transformers import CLIPProcessor, CLIPModel
import torch

# Vector DB
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Video Processing
import cv2
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from PIL import Image
import base64
from io import BytesIO


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

class Config:
    """Configurações centralizadas"""
    # AI Models
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLIP_MODEL = "openai/clip-vit-large-patch14"

    # Vector Database
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    COLLECTION_NAME = "video_clips"
    VECTOR_SIZE = 768  # CLIP ViT-L/14

    # Processing
    MAX_FRAMES_PER_CLIP = 8
    SCENE_THRESHOLD = 27.0

    # Paths
    CLIPS_DIR = Path("/data/video_clips")
    FRAMES_CACHE_DIR = Path("/data/frames_cache")


# ============================================================================
# MODELOS DE DADOS
# ============================================================================

@dataclass
class VideoClip:
    """Representa um clip no sistema"""
    id: str
    file_path: str
    duration: float

    # Análise visual (gerada por LLM)
    scene_description: Optional[str] = None
    visual_elements: Optional[List[str]] = None
    key_moments: Optional[List[Dict]] = None

    # Análise emocional
    emotional_tone: Optional[str] = None
    intensity: Optional[float] = None
    surprise_factor: Optional[float] = None
    viral_potential: Optional[float] = None

    # Análise narrativa
    narrative_arc: Optional[str] = None
    standalone: Optional[bool] = None

    # Metadata
    rights_cleared: bool = True
    times_used: int = 0

    # Embeddings
    embedding: Optional[np.ndarray] = None


@dataclass
class AnalysisResult:
    """Resultado da análise multimodal"""
    scene_description: str
    visual_elements: List[str]
    key_moments: List[Dict[str, any]]
    emotional_tone: str
    intensity: float
    surprise_factor: float
    viral_potential: float
    narrative_arc: str
    standalone: bool
    theme_scores: Dict[str, float]
    semantic_tags: List[str]


# ============================================================================
# EXTRAÇÃO DE FRAMES
# ============================================================================

class FrameExtractor:
    """Extrai frames-chave de vídeos usando detecção de mudança de cena"""

    def __init__(self, cache_dir: Path = Config.FRAMES_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_key_frames(self, video_path: str, max_frames: int = 8) -> List[Image.Image]:
        """
        Extrai frames-chave usando scene change detection

        Estratégia:
        1. Detecta mudanças de cena
        2. Extrai 1 frame por cena
        3. Se < max_frames, distribui uniformemente
        """
        # Cache lookup
        cache_key = self._get_cache_key(video_path)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached

        # Scene detection
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=Config.SCENE_THRESHOLD))

        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)
        scene_list = scene_manager.get_scene_list()
        video_manager.release()

        # Extrair frames
        if len(scene_list) == 0:
            # Sem mudanças de cena detectadas - distribuir uniformemente
            frames = self._extract_uniform_frames(video_path, max_frames)
        else:
            # 1 frame por cena (meio da cena)
            frames = []
            for scene in scene_list[:max_frames]:
                start_frame = scene[0].get_frames()
                end_frame = scene[1].get_frames()
                mid_frame = (start_frame + end_frame) // 2

                frame_img = self._extract_frame_at(video_path, mid_frame)
                if frame_img:
                    frames.append(frame_img)

        # Cache
        self._save_to_cache(cache_key, frames)

        return frames

    def _extract_uniform_frames(self, video_path: str, num_frames: int) -> List[Image.Image]:
        """Extrai frames uniformemente distribuídos"""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frames = []
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))

        cap.release()
        return frames

    def _extract_frame_at(self, video_path: str, frame_number: int) -> Optional[Image.Image]:
        """Extrai um frame específico"""
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()

        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame_rgb)
        return None

    def _get_cache_key(self, video_path: str) -> str:
        """Gera chave única para cache"""
        return hashlib.md5(video_path.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[List[Image.Image]]:
        """Carrega frames do cache"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            import pickle
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def _save_to_cache(self, cache_key: str, frames: List[Image.Image]):
        """Salva frames no cache"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        import pickle
        with open(cache_file, 'wb') as f:
            pickle.dump(frames, f)


# ============================================================================
# ANÁLISE MULTIMODAL COM LLM
# ============================================================================

class MultimodalAnalyzer:
    """Analisa clips usando Claude 3.5 Sonnet"""

    ANALYSIS_PROMPT = """
Você é um especialista em análise de vídeos para canais de compilação no YouTube estilo FailArmy e Refúgio Mental.

Analise este clip de vídeo (representado pelos frames-chave) e extraia as informações a seguir.

IMPORTANTE: Responda APENAS com JSON válido, sem markdown ou explicações adicionais.

{
  "scene_description": "Descrição objetiva em 2-3 frases do que acontece visualmente",

  "visual_elements": [
    "lista de elementos visuais importantes: pessoas, objetos, cenário, etc"
  ],

  "key_moments": [
    {"timestamp_relative": 0.0, "event": "início/setup"},
    {"timestamp_relative": 0.5, "event": "desenvolvimento"},
    {"timestamp_relative": 1.0, "event": "clímax/payoff"}
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
  },

  "semantic_tags": [
    "lista de 10-15 tags que capturam o SIGNIFICADO",
    "ex: reversão de expectativa, falha espetacular, reação cômica"
  ]
}

ESCALAS (todas 0-10):
- intensity: Quão intensa/energética é a cena
- surprise_factor: Elemento de surpresa/inesperado
- viral_potential: Potencial de compartilhamento/viralização
- theme_scores: Adequação para cada tema (0-10)

Analise agora:
"""

    def __init__(self, api_key: str = Config.ANTHROPIC_API_KEY):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_clip(self, frames: List[Image.Image]) -> AnalysisResult:
        """
        Analisa clip usando frames-chave

        Args:
            frames: Lista de frames PIL Image

        Returns:
            AnalysisResult com análise completa
        """
        # Converter frames para base64
        frame_contents = []
        for frame in frames[:Config.MAX_FRAMES_PER_CLIP]:
            b64_img = self._image_to_base64(frame)
            frame_contents.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64_img
                }
            })

        # Adicionar prompt
        frame_contents.append({
            "type": "text",
            "text": self.ANALYSIS_PROMPT
        })

        # Chamar Claude
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            temperature=0.3,
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

        analysis_json = json.loads(response_text)

        # Converter para dataclass
        return AnalysisResult(
            scene_description=analysis_json["scene_description"],
            visual_elements=analysis_json["visual_elements"],
            key_moments=analysis_json["key_moments"],
            emotional_tone=analysis_json["emotional_tone"],
            intensity=float(analysis_json["intensity"]),
            surprise_factor=float(analysis_json["surprise_factor"]),
            viral_potential=float(analysis_json["viral_potential"]),
            narrative_arc=analysis_json["narrative_arc"],
            standalone=analysis_json["standalone"],
            theme_scores=analysis_json["theme_scores"],
            semantic_tags=analysis_json["semantic_tags"]
        )

    def _image_to_base64(self, image: Image.Image, format: str = "JPEG") -> str:
        """Converte PIL Image para base64"""
        buffered = BytesIO()
        # Resize se muito grande (economizar tokens)
        if image.size[0] > 1024 or image.size[1] > 1024:
            image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode()


# ============================================================================
# GERAÇÃO DE EMBEDDINGS
# ============================================================================

class CLIPEmbedder:
    """Gera embeddings multimodais usando CLIP"""

    def __init__(self, model_name: str = Config.CLIP_MODEL):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        """
        Gera embedding de múltiplas imagens (average pooling)

        Returns:
            numpy array [768] (CLIP ViT-L/14)
        """
        inputs = self.processor(images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)

        # Average pooling
        avg_features = image_features.mean(dim=0)

        # Normalizar
        avg_features = avg_features / avg_features.norm()

        return avg_features.cpu().numpy()

    def embed_text(self, text: str) -> np.ndarray:
        """
        Gera embedding de texto

        Returns:
            numpy array [768]
        """
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)

        # Normalizar
        text_features = text_features / text_features.norm()

        return text_features.cpu().numpy()[0]

    def embed_multimodal(self, images: List[Image.Image], text: str,
                        weights: tuple = (0.7, 0.3)) -> np.ndarray:
        """
        Combina embeddings de imagem e texto

        Args:
            images: Frames do vídeo
            text: Descrição textual
            weights: (peso_imagem, peso_texto) - deve somar 1.0

        Returns:
            Embedding fusionado
        """
        img_emb = self.embed_images(images)
        txt_emb = self.embed_text(text)

        # Weighted fusion
        fused = weights[0] * img_emb + weights[1] * txt_emb

        # Re-normalizar
        fused = fused / np.linalg.norm(fused)

        return fused


# ============================================================================
# VECTOR DATABASE
# ============================================================================

class VectorDatabase:
    """Interface com Qdrant para armazenamento e busca vetorial"""

    def __init__(self, host: str = Config.QDRANT_HOST, port: int = Config.QDRANT_PORT):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = Config.COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self):
        """Cria collection se não existir"""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=Config.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

    def index_clip(self, clip: VideoClip):
        """Adiciona clip ao índice vetorial"""
        point = PointStruct(
            id=clip.id,
            vector=clip.embedding.tolist(),
            payload={
                "file_path": clip.file_path,
                "duration": clip.duration,
                "scene_description": clip.scene_description,
                "visual_elements": clip.visual_elements,
                "emotional_tone": clip.emotional_tone,
                "intensity": clip.intensity,
                "surprise_factor": clip.surprise_factor,
                "viral_potential": clip.viral_potential,
                "narrative_arc": clip.narrative_arc,
                "standalone": clip.standalone,
                "rights_cleared": clip.rights_cleared,
                "times_used": clip.times_used
            }
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )

    def search(self, query_vector: np.ndarray, limit: int = 100,
               filters: Optional[Dict] = None) -> List[Dict]:
        """
        Busca vetorial com filtros

        Args:
            query_vector: Embedding da query
            limit: Número de resultados
            filters: Filtros de metadata (ex: {"intensity": {"gte": 7.0}})

        Returns:
            Lista de resultados com score
        """
        # Construir filtro Qdrant
        qdrant_filter = None
        if filters:
            qdrant_filter = self._build_filter(filters)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=limit,
            query_filter=qdrant_filter
        )

        return [
            {
                "id": r.id,
                "score": r.score,
                **r.payload
            }
            for r in results
        ]

    def _build_filter(self, filters: Dict):
        """Converte dicionário de filtros para formato Qdrant"""
        from qdrant_client.models import Filter, FieldCondition, Range, MatchValue

        conditions = []

        for key, value in filters.items():
            if isinstance(value, dict):
                # Range filter
                if "gte" in value or "lte" in value:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            range=Range(
                                gte=value.get("gte"),
                                lte=value.get("lte")
                            )
                        )
                    )
            else:
                # Exact match
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )

        return Filter(must=conditions) if conditions else None


# ============================================================================
# CURADOR INTELIGENTE
# ============================================================================

class IntelligentCurator:
    """Sistema de curadoria RAG multimodal"""

    def __init__(self):
        self.frame_extractor = FrameExtractor()
        self.analyzer = MultimodalAnalyzer()
        self.embedder = CLIPEmbedder()
        self.vector_db = VectorDatabase()

    def index_video_clip(self, video_path: str, clip_id: str) -> VideoClip:
        """
        Pipeline completo de indexação de um clip

        1. Extrai frames-chave
        2. Analisa com LLM multimodal
        3. Gera embeddings
        4. Armazena no vector DB
        """
        print(f"📹 Indexando {clip_id}...")

        # 1. Extrair frames
        frames = self.frame_extractor.extract_key_frames(video_path)
        print(f"  ✓ Extraídos {len(frames)} frames")

        # 2. Analisar com LLM
        analysis = self.analyzer.analyze_clip(frames)
        print(f"  ✓ Análise: {analysis.emotional_tone}, intensidade={analysis.intensity}")

        # 3. Gerar embeddings
        embedding = self.embedder.embed_multimodal(
            images=frames,
            text=analysis.scene_description,
            weights=(0.7, 0.3)  # 70% visual, 30% semântico
        )
        print(f"  ✓ Embedding gerado: shape={embedding.shape}")

        # 4. Criar objeto VideoClip
        # Obter duração do vídeo
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps > 0 else 0
        cap.release()

        clip = VideoClip(
            id=clip_id,
            file_path=video_path,
            duration=duration,
            scene_description=analysis.scene_description,
            visual_elements=analysis.visual_elements,
            key_moments=analysis.key_moments,
            emotional_tone=analysis.emotional_tone,
            intensity=analysis.intensity,
            surprise_factor=analysis.surprise_factor,
            viral_potential=analysis.viral_potential,
            narrative_arc=analysis.narrative_arc,
            standalone=analysis.standalone,
            embedding=embedding
        )

        # 5. Indexar no vector DB
        self.vector_db.index_clip(clip)
        print(f"  ✓ Indexado no Qdrant")

        return clip

    def curate_clips_for_theme(self, theme: str, target_duration: int,
                               style: str = "energetic") -> List[Dict]:
        """
        Seleciona clips para um tema usando RAG multimodal

        Args:
            theme: Tema do vídeo (ex: "fails épicos de skate")
            target_duration: Duração alvo em segundos
            style: Estilo do vídeo

        Returns:
            Lista de clips selecionados com metadata
        """
        print(f"\n🎬 Curando clips para tema: '{theme}'")
        print(f"   Duração alvo: {target_duration}s, Estilo: {style}")

        # 1. Expandir query com LLM
        expanded_query = self._expand_query(theme, style)
        print(f"\n📝 Query expandida:")
        print(f"   Visual: {expanded_query['visual'][:100]}...")

        # 2. Gerar embedding da query
        query_embedding = self.embedder.embed_text(expanded_query['combined'])

        # 3. Definir filtros baseados no estilo
        filters = self._get_style_filters(style)

        # 4. Busca vetorial
        print(f"\n🔍 Buscando no vector database...")
        candidates = self.vector_db.search(
            query_vector=query_embedding,
            limit=100,
            filters=filters
        )
        print(f"   Encontrados {len(candidates)} candidatos")

        # 5. Reranking com critérios adicionais
        print(f"\n🎯 Reranking candidatos...")
        reranked = self._rerank_candidates(candidates, theme, style)

        # 6. Seleção final com diversidade (MMR)
        print(f"\n✨ Aplicando diversidade (MMR)...")
        final_selection = self._apply_mmr(
            candidates=reranked[:50],
            target_duration=target_duration,
            lambda_param=0.7
        )

        print(f"\n✅ Selecionados {len(final_selection)} clips ({sum(c['duration'] for c in final_selection):.1f}s)")

        return final_selection

    def _expand_query(self, theme: str, style: str) -> Dict[str, str]:
        """Expande query usando LLM (GPT-4o ou Claude)"""
        # Simplificado - em produção, chamar LLM
        expansions = {
            "energetic": {
                "visual": f"{theme} com ação intensa, movimento rápido",
                "emotion": "surpresa, comédia, adrenalina",
                "avoid": "cenas paradas, conteúdo sensível"
            },
            "chill": {
                "visual": f"{theme} com atmosfera calma, momentos satisfatórios",
                "emotion": "wholesome, relaxante, positivo",
                "avoid": "conteúdo agressivo, muito intenso"
            },
            "emotional": {
                "visual": f"{theme} com momentos tocantes, reações genuínas",
                "emotion": "emocionante, inspirador, comovente",
                "avoid": "comédia exagerada, caos"
            }
        }

        exp = expansions.get(style, expansions["energetic"])
        exp["combined"] = f"{exp['visual']}. Tom emocional: {exp['emotion']}"

        return exp

    def _get_style_filters(self, style: str) -> Dict:
        """Define filtros baseados no estilo"""
        base_filters = {
            "rights_cleared": True,
            "standalone": True
        }

        if style == "energetic":
            base_filters["intensity"] = {"gte": 7.0}
        elif style == "chill":
            base_filters["intensity"] = {"lte": 6.0}
        elif style == "emotional":
            base_filters["viral_potential"] = {"gte": 7.0}

        return base_filters

    def _rerank_candidates(self, candidates: List[Dict],
                          theme: str, style: str) -> List[Dict]:
        """Reranking com critérios adicionais"""
        # Boost baseado em viral_potential e surprise_factor
        for c in candidates:
            bonus = 0.0
            bonus += c.get("viral_potential", 0) * 0.1
            bonus += c.get("surprise_factor", 0) * 0.1

            # Penalizar se foi usado recentemente
            if c.get("times_used", 0) > 5:
                bonus -= 0.2

            c["final_score"] = c["score"] + bonus

        # Ordenar por score final
        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)

    def _apply_mmr(self, candidates: List[Dict], target_duration: int,
                   lambda_param: float = 0.7) -> List[Dict]:
        """
        Maximal Marginal Relevance - balanceia relevância e diversidade

        Args:
            lambda_param: 1.0 = só relevância, 0.0 = só diversidade
        """
        selected = []
        total_duration = 0.0

        while candidates and total_duration < target_duration * 1.1:
            if not selected:
                # Primeiro: mais relevante
                best = candidates.pop(0)
                selected.append(best)
                total_duration += best["duration"]
            else:
                # Próximos: balancear relevância e diversidade
                mmr_scores = []

                for candidate in candidates[:20]:  # Top 20 restantes
                    relevance = candidate["final_score"]

                    # Diversidade: quão diferente dos já selecionados?
                    # Simplificado: comparar emotional_tone
                    diversity = 1.0
                    for sel in selected[-3:]:  # Últimos 3
                        if sel.get("emotional_tone") == candidate.get("emotional_tone"):
                            diversity *= 0.7

                    mmr = lambda_param * relevance + (1 - lambda_param) * diversity
                    mmr_scores.append((mmr, candidate))

                # Selecionar melhor MMR
                mmr_scores.sort(reverse=True, key=lambda x: x[0])
                best = mmr_scores[0][1]

                candidates.remove(best)
                selected.append(best)
                total_duration += best["duration"]

        return selected


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Inicializar curador
    curator = IntelligentCurator()

    # FASE 1: Indexar clips (fazer 1x para cada clip novo)
    print("=" * 70)
    print("FASE 1: INDEXAÇÃO DE CLIPS")
    print("=" * 70)

    sample_clips = [
        "/data/clips/skate_fail_01.mp4",
        "/data/clips/skate_fail_02.mp4",
        "/data/clips/skate_epic_01.mp4"
    ]

    for i, clip_path in enumerate(sample_clips):
        if Path(clip_path).exists():
            clip_id = f"clip_{i:04d}"
            curator.index_video_clip(clip_path, clip_id)
        else:
            print(f"⚠️  Arquivo não encontrado: {clip_path}")

    # FASE 2: Curar clips para produção
    print("\n" + "=" * 70)
    print("FASE 2: CURADORIA PARA PRODUÇÃO")
    print("=" * 70)

    selected_clips = curator.curate_clips_for_theme(
        theme="fails épicos de skate com quedas dramáticas",
        target_duration=600,  # 10 minutos
        style="energetic"
    )

    # Exibir resultados
    print("\n📊 CLIPS SELECIONADOS:\n")
    for i, clip in enumerate(selected_clips[:10], 1):
        print(f"{i}. {clip['id']}")
        print(f"   Descrição: {clip['scene_description'][:80]}...")
        print(f"   Score: {clip['final_score']:.3f} | Intensidade: {clip['intensity']}/10")
        print(f"   Duração: {clip['duration']:.1f}s | Viral: {clip['viral_potential']}/10")
        print()

    print(f"Total: {len(selected_clips)} clips, {sum(c['duration'] for c in selected_clips):.1f}s")
