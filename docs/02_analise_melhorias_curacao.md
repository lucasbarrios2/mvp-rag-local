# Análise Detalhada: Melhorias no Sistema de Curadoria de Vídeos
**Janeiro 2026 - Estado da Arte em AI Multimodal**

## 🎯 Problema Central

**Situação Atual**: Sistema básico usa apenas tags textuais e metadata estruturada (quality_score, engagement_rate). Isso limita severamente:

- ❌ Não entende o **conteúdo visual** do clip (o que realmente acontece na cena)
- ❌ Não captura **emoções** ou **tensão dramática**
- ❌ Não identifica **elementos visuais** específicos (skatepark, rampa, pessoa caindo)
- ❌ Busca é **léxica** (keywords), não **semântica** (significado)
- ❌ Depende de **rotulagem manual** trabalhosa e inconsistente

**Objetivo**: Criar um sistema que "assiste" e "compreende" cada clip, permitindo curadoria criativa e contextual.

---

## 🧠 ESTRATÉGIA 1: RAG Multimodal para Vídeos

### Conceito

RAG (Retrieval-Augmented Generation) tradicional usa embeddings de **texto**. RAG multimodal usa embeddings de **vídeo + áudio + texto**, permitindo busca semântica profunda.

### Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE DE INDEXAÇÃO (Executado 1x por clip novo)        │
└─────────────────────────────────────────────────────────────┘

Clip de Vídeo (video.mp4)
    ↓
┌───────────────────────────────────────────────────────────┐
│ 1. EXTRAÇÃO DE FRAMES CHAVE                               │
│    - Algoritmo: Scene Change Detection                     │
│    - Output: 5-10 frames representativos por clip         │
│    - Tool: PySceneDetect ou OpenCV                         │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 2. ANÁLISE MULTIMODAL COM LLM                             │
│    Model: GPT-4 Vision / Claude 3.5 Sonnet / Gemini 2.0  │
│                                                            │
│    Input: Frames + prompt estruturado                      │
│    Output: Descrição semântica rica                        │
│                                                            │
│    Exemplo de output:                                      │
│    {                                                       │
│      "scene_description": "Skatista tenta flip em rampa   │
│                            alta, perde equilíbrio e cai    │
│                            de forma cômica",               │
│      "emotional_tone": "cômico, leve, sem dano grave",     │
│      "key_moments": [                                      │
│        {"timestamp": 0.5, "event": "preparação"},         │
│        {"timestamp": 2.1, "event": "salto"},              │
│        {"timestamp": 3.8, "event": "queda"}               │
│      ],                                                    │
│      "visual_elements": ["rampa", "skate", "pessoa",      │
│                          "céu aberto", "público ao fundo"],│
│      "intensity": 8.5,                                     │
│      "surprise_factor": 9.0,                               │
│      "narrative_arc": "setup -> escalation -> payoff"      │
│    }                                                       │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 3. GERAÇÃO DE EMBEDDINGS                                  │
│    Model: CLIP / VideoMAE / ImageBind                     │
│                                                            │
│    - Visual embedding: 512-dim vector dos frames          │
│    - Text embedding: 512-dim vector da descrição          │
│    - Audio embedding: 512-dim do áudio (gritos, música)   │
│    - Multimodal fusion: Combina os 3 em embedding único   │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 4. ARMAZENAMENTO EM VECTOR DB                             │
│    Database: Qdrant / Pinecone / Weaviate / Chroma        │
│                                                            │
│    Cada clip vira um documento:                            │
│    {                                                       │
│      "id": "clip_12345",                                   │
│      "file_path": "/videos/clip_12345.mp4",               │
│      "vector": [0.123, -0.456, ...],  # embedding         │
│      "metadata": {                                         │
│        "description": "...",                               │
│        "emotional_tone": "cômico",                         │
│        "intensity": 8.5,                                   │
│        "visual_elements": [...],                           │
│        "duration": 5.2,                                    │
│        "key_moments": [...]                                │
│      }                                                     │
│    }                                                       │
└───────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PIPELINE DE BUSCA (Executado cada produção)               │
└─────────────────────────────────────────────────────────────┘

Usuário: "fails épicos de skate com quedas dramáticas"
    ↓
┌───────────────────────────────────────────────────────────┐
│ 1. QUERY EXPANSION COM LLM                                │
│    Input: Query original                                   │
│    Output: Query expandida semanticamente                  │
│                                                            │
│    "fails épicos de skate com quedas dramáticas"          │
│    ↓                                                       │
│    {                                                       │
│      "core_concept": "falhas espetaculares no skate",     │
│      "visual_requirements": [                              │
│        "rampa alta ou obstáculo complexo",                │
│        "momento de impacto visível",                       │
│        "reação de surpresa"                                │
│      ],                                                    │
│      "emotional_requirements": [                           │
│        "tensão crescente",                                 │
│        "payoff satisfatório"                               │
│      ],                                                    │
│      "avoid": ["lesões graves", "conteúdo violento"]      │
│    }                                                       │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 2. EMBEDDING DA QUERY                                      │
│    - Gera embedding da query expandida                     │
│    - Usa o mesmo modelo (CLIP/VideoMAE)                   │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 3. BUSCA VETORIAL HÍBRIDA                                 │
│                                                            │
│    a) Similarity Search                                    │
│       - Cosine similarity entre query e clips              │
│       - Top 100 candidatos                                 │
│                                                            │
│    b) Metadata Filtering                                   │
│       - intensity >= 7.0                                   │
│       - emotional_tone in ["cômico", "épico"]             │
│       - duration between 3-15s                             │
│       - rights_cleared = true                              │
│                                                            │
│    c) Reranking com LLM (top 100 → top 30)                │
│       - LLM analisa relevância contextual                  │
│       - Considera narrative_arc                            │
│       - Elimina duplicatas semânticas                      │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ 4. DIVERSIDADE E BALANCEAMENTO                            │
│    - MMR (Maximal Marginal Relevance)                     │
│    - Garante variedade visual                              │
│    - Evita clips muito similares consecutivos              │
└───────────────────────────────────────────────────────────┘
    ↓
📦 30 clips altamente relevantes e diversos
```

---

## 🤖 ESTRATÉGIA 2: Análise Multimodal com LLMs de Janeiro 2026

### Modelos Disponíveis (Estado da Arte)

| Modelo | Capacidades | Melhor Para | Custo |
|--------|-------------|-------------|-------|
| **GPT-4 Vision (GPT-4o)** | Análise de imagens, vídeo (via frames), raciocínio visual | Descrições criativas, entendimento contextual | $$$ |
| **Claude 3.5 Sonnet** | Análise visual profunda, precisão técnica | Análise detalhada, classificação precisa | $$ |
| **Gemini 2.0 Flash** | Multimodal nativo (vídeo direto), rápido | Processamento em larga escala | $ |
| **LLaVA/LLaVA-NeXT** | Open-source, customizável | Deploy local, privacy | $ (infra) |

### Prompt Engineering para Análise de Clips

```python
ANALYSIS_PROMPT = """
Você é um especialista em análise de vídeos para canais de compilação no YouTube.

Analise este clip de vídeo e extraia:

## 1. DESCRIÇÃO DA CENA (2-3 frases)
Descreva O QUE acontece visualmente, de forma clara e objetiva.

## 2. ELEMENTOS VISUAIS
Liste todos os elementos importantes: pessoas, objetos, cenário, ações.

## 3. NARRATIVA E TIMING
- Setup (0-X segundos): O que prepara a cena?
- Build-up (X-Y segundos): Como a tensão aumenta?
- Payoff (Y-Z segundos): Qual o momento crucial/engraçado/épico?

## 4. ANÁLISE EMOCIONAL (escala 0-10)
- Intensidade: ___
- Fator surpresa: ___
- Impacto visual: ___
- Apelo cômico: ___
- Tom emocional: [cômico / épico / emocionante / tenso / fofo]

## 5. ADEQUAÇÃO PARA COMPILAÇÃO
- Standalone: Funciona sem contexto? [sim/não]
- Momento viral: Tem potencial de compartilhamento? [0-10]
- Público-alvo: [crianças / adolescentes / adultos / geral]

## 6. TAGS SEMÂNTICAS
Liste 10-15 tags que capturam o SIGNIFICADO (não só objetos visíveis).
Ex: "reversão de expectativa", "falha espetacular", "reação cômica"

## 7. ADEQUAÇÃO PARA TEMAS
Dê score 0-10 para adequação aos temas:
- Fails/Acidentes: ___
- Esportes radicais: ___
- Comédia: ___
- Momentos wholesome: ___
- "Instant regret": ___
- Tutorial fail: ___

Responda em JSON estruturado.
"""

def analyze_clip_with_llm(clip_path: str, frames: list) -> dict:
    """
    Analisa clip usando LLM multimodal
    """
    import anthropic

    client = anthropic.Anthropic(api_key="...")

    # Preparar frames em base64
    frame_images = [encode_image_base64(f) for f in frames[:8]]

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                *[{"type": "image", "source": {"type": "base64",
                   "media_type": "image/jpeg", "data": img}}
                  for img in frame_images],
                {"type": "text", "text": ANALYSIS_PROMPT}
            ]
        }]
    )

    # Parse JSON response
    analysis = json.loads(message.content[0].text)
    return analysis
```

---

## 🔧 ESTRATÉGIA 3: Ferramentas Especializadas de AI

### 3.1 CLIP (OpenAI) - Embedding Multimodal

```python
from transformers import CLIPProcessor, CLIPModel
import torch

class ClipEmbedder:
    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

    def embed_image(self, image):
        inputs = self.processor(images=image, return_tensors="pt")
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        return image_features.numpy()[0]

    def embed_text(self, text):
        inputs = self.processor(text=text, return_tensors="pt", padding=True)
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
        return text_features.numpy()[0]

    def similarity(self, image, text):
        """Quão bem o texto descreve a imagem (0-1)"""
        img_emb = self.embed_image(image)
        txt_emb = self.embed_text(text)
        return cosine_similarity(img_emb, txt_emb)
```

**Uso**: Validar se frames realmente correspondem à descrição gerada.

### 3.2 VideoMAE - Entendimento Temporal

```python
from transformers import VideoMAEForVideoClassification

class VideoTemporalAnalyzer:
    """
    Analisa MOVIMENTO e AÇÃO ao longo do tempo
    Não apenas frames estáticos
    """
    def __init__(self):
        self.model = VideoMAEForVideoClassification.from_pretrained(
            "MCG-NJU/videomae-base-finetuned-kinetics"
        )

    def classify_action(self, video_path):
        """
        Classifica a AÇÃO principal
        Ex: "skateboarding", "falling", "jumping"
        """
        frames = extract_frames(video_path, num_frames=16)
        inputs = preprocess_frames(frames)
        outputs = self.model(inputs)
        return decode_action(outputs)

    def get_action_intensity_curve(self, video_path):
        """
        Retorna curva de intensidade ao longo do tempo
        Útil para detectar "momento do impacto"
        """
        segments = split_into_segments(video_path, duration=0.5)
        intensities = [self.get_intensity(seg) for seg in segments]
        return intensities
```

**Uso**: Detectar "pico de ação" para thumbnail, identificar momento exato do fail.

### 3.3 Whisper (OpenAI) - Transcrição de Áudio

```python
import whisper

class AudioAnalyzer:
    def __init__(self):
        self.model = whisper.load_model("large-v3")

    def transcribe_and_analyze(self, video_path):
        """
        Extrai falas, sons, música de fundo
        """
        result = self.model.transcribe(video_path, language="pt")

        # Detectar eventos sonoros
        sound_events = self.detect_sound_events(video_path)

        return {
            "transcript": result["text"],
            "sound_events": sound_events,  # ["grito", "risada", "impacto"]
            "has_speech": len(result["segments"]) > 0,
            "background_music": self.detect_music(video_path)
        }

    def detect_sound_events(self, video_path):
        """
        Usa modelo treinado para detectar:
        - Risadas
        - Gritos
        - Impactos
        - Multidão reagindo
        """
        # Implementar com modelo especializado (ex: PANNs)
        pass
```

**Uso**: "Finds com reação sonora da plateia" - buscar clips com risadas/gritos.

### 3.4 ImageBind (Meta) - Embedding Tudo-em-Um

```python
from imagebind import data, models

class UnifiedEmbedder:
    """
    Embeddings unificados de: vídeo, áudio, texto, imagem
    Todos no mesmo espaço vetorial!
    """
    def __init__(self):
        self.model = models.imagebind_huge(pretrained=True)

    def embed_multimodal(self, video_path, description):
        inputs = {
            "vision": data.load_and_transform_video(video_path),
            "audio": data.load_and_transform_audio(video_path),
            "text": data.load_and_transform_text([description])
        }

        with torch.no_grad():
            embeddings = self.model(inputs)

        # Fusão de embeddings
        unified = torch.cat([
            embeddings["vision"],
            embeddings["audio"],
            embeddings["text"]
        ], dim=-1)

        return unified.numpy()[0]
```

**Uso**: Busca que considera visual + áudio + semântica simultaneamente.

---

## 📊 ESTRATÉGIA 4: Sistema Híbrido (Recomendação Final)

### Arquitetura Proposta para Produção

```
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 1: INDEXAÇÃO OFFLINE (Background Job)              │
└─────────────────────────────────────────────────────────────┘

Para cada clip novo:
1. Extrai frames (PySceneDetect)
2. Analisa com Claude 3.5 Sonnet → descrição rica
3. Transcreve áudio (Whisper)
4. Gera embeddings (ImageBind)
5. Salva tudo no Qdrant + PostgreSQL

┌─────────────────────────────────────────────────────────────┐
│  CAMADA 2: CURAÇÃO INTELIGENTE (Query Time)                │
└─────────────────────────────────────────────────────────────┘

Tema do usuário → Query Expansion (GPT-4o)
    ↓
Busca Vetorial (Qdrant) → Top 100 candidatos
    ↓
Reranking com LLM → Top 50 relevantes
    ↓
Filtragem por diversidade (MMR) → Top 30
    ↓
Análise de narrativa (GPT-4o) → Seleciona final

┌─────────────────────────────────────────────────────────────┐
│  CAMADA 3: VALIDAÇÃO CRIATIVA (Pre-Render)                 │
└─────────────────────────────────────────────────────────────┘

LLM analisa sequência de clips:
- Há flow narrativo?
- Intensidade cresce ao longo do vídeo?
- Clips fazem sentido juntos?
- Falta algum "tipo" de momento?

Se não: volta para curação com feedback
```

### Dados a Persistir (PostgreSQL)

```sql
-- Tabela de clips com análise rica
CREATE TABLE video_clips (
    id UUID PRIMARY KEY,
    file_path TEXT NOT NULL,
    duration FLOAT NOT NULL,

    -- Metadata básica
    uploaded_at TIMESTAMP,
    rights_cleared BOOLEAN,
    source TEXT,

    -- Análise visual (gerada por LLM)
    scene_description TEXT,
    visual_elements JSONB,  -- ["rampa", "skate", "pessoa"]
    key_moments JSONB,      -- [{"timestamp": 2.1, "event": "salto"}]

    -- Análise emocional
    emotional_tone TEXT,    -- "cômico", "épico", "wholesome"
    intensity FLOAT,        -- 0-10
    surprise_factor FLOAT,  -- 0-10
    viral_potential FLOAT,  -- 0-10

    -- Análise narrativa
    narrative_arc TEXT,     -- "setup -> escalation -> payoff"
    standalone BOOLEAN,     -- Funciona sem contexto?

    -- Análise de áudio
    audio_transcript TEXT,
    sound_events TEXT[],    -- ["grito", "risada", "impacto"]
    has_speech BOOLEAN,

    -- Métricas de performance
    times_used INTEGER DEFAULT 0,
    avg_retention_rate FLOAT,  -- Quantos % assistem quando esse clip aparece

    -- Embeddings (referência para vector DB)
    embedding_id TEXT       -- ID no Qdrant
);

-- Tabela de temas semânticos
CREATE TABLE semantic_tags (
    clip_id UUID REFERENCES video_clips(id),
    tag TEXT,
    confidence FLOAT,
    PRIMARY KEY (clip_id, tag)
);

-- Índices para busca rápida
CREATE INDEX idx_emotional_tone ON video_clips(emotional_tone);
CREATE INDEX idx_intensity ON video_clips(intensity);
CREATE INDEX idx_viral_potential ON video_clips(viral_potential);
CREATE GIN INDEX idx_visual_elements ON video_clips USING gin(visual_elements);
```

---

## 💡 Exemplo Prático Completo

```python
# Query do usuário
theme = "fails épicos de skate com quedas dramáticas"

# 1. Expandir query com LLM
expanded_query = expand_query_with_llm(theme)
# → {
#     "visual": "rampa alta, pessoa em skate perdendo equilíbrio",
#     "action": "queda, falha, acidente não grave",
#     "emotion": "surpresa, comédia, drama leve",
#     "avoid": "lesões sérias, sangue"
#   }

# 2. Busca vetorial
from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)
query_vector = embedder.embed_text(expanded_query["visual"])

results = client.search(
    collection_name="video_clips",
    query_vector=query_vector,
    limit=100,
    query_filter={
        "must": [
            {"key": "intensity", "range": {"gte": 7.0}},
            {"key": "rights_cleared", "match": {"value": True}},
            {"key": "emotional_tone", "match": {"value": "cômico"}}
        ]
    }
)

# 3. Reranking com LLM
clip_ids = [r.id for r in results]
clips_metadata = fetch_clips_from_db(clip_ids)

reranked = rerank_with_llm(
    query=theme,
    candidates=clips_metadata,
    criteria=["relevance", "narrative_fit", "uniqueness"]
)

# 4. Seleção final com diversidade
final_selection = apply_mmr(
    candidates=reranked[:50],
    target_count=30,
    lambda_param=0.7  # Balance relevance vs diversity
)

print(f"Selecionados {len(final_selection)} clips:")
for clip in final_selection[:5]:
    print(f"- {clip['scene_description'][:80]}...")
    print(f"  Intensidade: {clip['intensity']}/10, Viral: {clip['viral_potential']}/10")
```

---

## 🚀 Roadmap de Implementação

### Fase 1: MVP (2-3 semanas)
- [ ] Pipeline de extração de frames
- [ ] Integração com Claude 3.5 Sonnet para análise
- [ ] Schema PostgreSQL básico
- [ ] Busca simples por descrição textual

### Fase 2: RAG Básico (3-4 semanas)
- [ ] Setup Qdrant vector database
- [ ] Integração CLIP para embeddings
- [ ] Busca vetorial híbrida (texto + metadata)
- [ ] Reranking com LLM

### Fase 3: Multimodal Completo (4-6 semanas)
- [ ] Integração ImageBind
- [ ] Análise de áudio (Whisper)
- [ ] Query expansion automática
- [ ] Pipeline de análise narrativa

### Fase 4: Otimização (Contínuo)
- [ ] Fine-tuning de embeddings no domínio
- [ ] A/B testing de algoritmos de ranqueamento
- [ ] Feedback loop (clips usados → melhor ranqueamento)
- [ ] Cache inteligente de análises

---

## 💰 Estimativa de Custos (Produção)

### Indexação (1x por clip)
- Claude 3.5 Sonnet: ~$0.003 por clip (análise de 8 frames)
- CLIP embeddings: Gratuito (local)
- Armazenamento Qdrant: ~$0.0001 por clip/mês
- **Total por clip: ~$0.003 one-time + $0.0001/mês**

### Curação (por vídeo produzido)
- Query expansion: ~$0.001
- Reranking (100 clips): ~$0.01
- Validação narrativa: ~$0.002
- **Total por vídeo: ~$0.013**

Para canal com 1000 clips e 30 vídeos/mês:
- Setup inicial: $3
- Operação mensal: ~$0.50

**Extremamente viável!**

---

## 🎓 Conclusão e Recomendações

### O que Implementar AGORA
1. **Pipeline de análise com Claude 3.5 Sonnet** - ROI imediato na qualidade
2. **PostgreSQL com metadata rica** - Base para tudo
3. **Busca textual melhorada** - Sem precisar de vector DB inicialmente

### O que Implementar em Q2 2026
1. **RAG com Qdrant + CLIP** - Quando tiver 500+ clips
2. **Query expansion automática** - Depois de validar manualmente
3. **Feedback loop** - Quando tiver métricas de performance

### O que NÃO Fazer (por enquanto)
- ❌ Fine-tuning de modelos próprios (desnecessário)
- ❌ Múltiplos vector databases (começar com 1)
- ❌ Análise frame-by-frame (muito caro)

---

**Próximo Arquivo**: Implementação detalhada do RAG multimodal em Python
