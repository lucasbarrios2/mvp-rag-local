# Guia Quick Start: Sistema de Produção de Vídeos
**Do Zero ao Primeiro Vídeo em 2 Horas**

## 🎯 Objetivo

Criar um protótipo funcional que:
1. Indexa 10 clips de vídeo
2. Analisa com IA multimodal
3. Seleciona clips para um tema
4. Mostra resultados

**Não faremos** (por enquanto): renderização, API, produção completa.

---

## 📋 Pré-requisitos

```bash
# Sistema operacional
- Windows 10/11, macOS, ou Linux
- Python 3.10+
- 8GB+ RAM
- GPU (opcional, acelera)

# Contas necessárias
- Anthropic API key (Claude) - https://console.anthropic.com
- Qdrant Cloud (free tier) ou Docker local
```

---

## 🚀 Setup Rápido (30 min)

### 1. Criar Ambiente Virtual

```bash
# Criar projeto
mkdir video-curator
cd video-curator

# Criar venv
python -m venv venv

# Ativar
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2. Instalar Dependências

```bash
# Criar requirements.txt
cat > requirements.txt << EOF
anthropic>=0.40.0
transformers>=4.36.0
torch>=2.1.0
qdrant-client>=1.7.0
opencv-python>=4.8.0
pillow>=10.1.0
numpy>=1.24.0
scenedetect[opencv]>=0.6.3
python-dotenv>=1.0.0
tqdm>=4.66.0
EOF

# Instalar
pip install -r requirements.txt
```

### 3. Configurar API Keys

```bash
# Criar .env
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-api03-...
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Vazio se local
EOF
```

### 4. Subir Qdrant (Docker)

```bash
# Opção 1: Docker local
docker run -p 6333:6333 qdrant/qdrant

# Opção 2: Qdrant Cloud (free)
# Criar cluster em https://cloud.qdrant.io
# Usar URL e API key no .env
```

---

## 💻 Código Mínimo Funcional

### `simple_curator.py`

```python
"""
Curador Simplificado - Versão Quick Start
Indexa e busca clips com IA multimodal
"""

import os
import json
from pathlib import Path
from typing import List
import anthropic
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import cv2
import base64
from io import BytesIO
from dotenv import load_dotenv

# Carregar config
load_dotenv()

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")


# ============================================================================
# EXTRATOR DE FRAMES SIMPLES
# ============================================================================

def extract_frames_simple(video_path: str, num_frames: int = 4) -> List[Image.Image]:
    """Extrai frames uniformemente distribuídos"""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frames = []
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(frame_rgb))

    cap.release()
    return frames


# ============================================================================
# ANÁLISE COM CLAUDE
# ============================================================================

def analyze_with_claude(frames: List[Image.Image]) -> dict:
    """Analisa frames com Claude 3.5 Sonnet"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Converter frames para base64
    frame_contents = []
    for frame in frames:
        buffered = BytesIO()
        frame.thumbnail((512, 512))  # Reduzir tamanho
        frame.save(buffered, format="JPEG")
        b64 = base64.b64encode(buffered.getvalue()).decode()

        frame_contents.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}
        })

    # Prompt simplificado
    prompt = """
Analise este vídeo e responda em JSON:

{
  "description": "Descrição breve (1 frase)",
  "emotion": "cômico|épico|wholesome|tenso",
  "intensity": 7.5,
  "viral_score": 8.0,
  "tags": ["tag1", "tag2", "tag3"]
}
"""

    frame_contents.append({"type": "text", "text": prompt})

    # Chamar API
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=512,
        messages=[{"role": "user", "content": frame_contents}]
    )

    # Parse JSON
    text = response.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]

    return json.loads(text)


# ============================================================================
# EMBEDDINGS COM CLIP
# ============================================================================

class SimpleEmbedder:
    def __init__(self):
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    def embed(self, images: List[Image.Image]) -> np.ndarray:
        """Gera embedding de imagens"""
        inputs = self.processor(images=images, return_tensors="pt", padding=True)
        features = self.model.get_image_features(**inputs)
        avg = features.mean(dim=0)
        avg = avg / avg.norm()
        return avg.detach().numpy()

    def embed_text(self, text: str) -> np.ndarray:
        """Gera embedding de texto"""
        inputs = self.processor(text=[text], return_tensors="pt")
        features = self.model.get_text_features(**inputs)
        features = features / features.norm()
        return features.detach().numpy()[0]


# ============================================================================
# CURADOR
# ============================================================================

class SimpleCurator:
    def __init__(self):
        self.embedder = SimpleEmbedder()
        self.db = QdrantClient(url=QDRANT_URL)
        self._init_collection()

    def _init_collection(self):
        """Cria collection se não existir"""
        collections = [c.name for c in self.db.get_collections().collections]
        if "clips" not in collections:
            self.db.create_collection(
                collection_name="clips",
                vectors_config=VectorParams(size=512, distance=Distance.COSINE)
            )

    def index_clip(self, video_path: str, clip_id: str):
        """Indexa um clip"""
        print(f"\n📹 Indexando {clip_id}...")

        # 1. Extrair frames
        frames = extract_frames_simple(video_path, num_frames=4)
        print(f"  ✓ {len(frames)} frames extraídos")

        # 2. Analisar
        analysis = analyze_with_claude(frames)
        print(f"  ✓ Análise: {analysis['emotion']}, score={analysis['viral_score']}")

        # 3. Embeddings
        embedding = self.embedder.embed(frames)
        print(f"  ✓ Embedding gerado")

        # 4. Salvar no Qdrant
        self.db.upsert(
            collection_name="clips",
            points=[PointStruct(
                id=clip_id,
                vector=embedding.tolist(),
                payload={
                    "path": video_path,
                    "description": analysis["description"],
                    "emotion": analysis["emotion"],
                    "intensity": analysis["intensity"],
                    "viral_score": analysis["viral_score"],
                    "tags": analysis["tags"]
                }
            )]
        )
        print(f"  ✓ Salvo no banco")

    def search(self, query: str, limit: int = 10):
        """Busca clips por query"""
        print(f"\n🔍 Buscando: '{query}'")

        # Embedding da query
        query_emb = self.embedder.embed_text(query)

        # Buscar
        results = self.db.search(
            collection_name="clips",
            query_vector=query_emb.tolist(),
            limit=limit
        )

        print(f"  Encontrados {len(results)} resultados\n")

        # Exibir
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r.score:.3f}] {r.payload['description']}")
            print(f"   Emoção: {r.payload['emotion']}, Viral: {r.payload['viral_score']}")
            print(f"   Tags: {', '.join(r.payload['tags'])}")
            print()

        return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys

    curator = SimpleCurator()

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python simple_curator.py index <video.mp4> <id>")
        print("  python simple_curator.py search <query>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "index":
        video_path = sys.argv[2]
        clip_id = sys.argv[3] if len(sys.argv) > 3 else Path(video_path).stem
        curator.index_clip(video_path, clip_id)

    elif command == "search":
        query = " ".join(sys.argv[2:])
        curator.search(query, limit=5)

    print("\n✅ Concluído!")
```

---

## 🎬 Testando o Sistema

### 1. Preparar Clips de Teste

```bash
# Criar diretório
mkdir test_clips

# Baixar alguns clips de teste (Creative Commons)
# Ou usar seus próprios vídeos curtos (3-15 segundos)

# Exemplo: converter um vídeo longo em clips
ffmpeg -i video_longo.mp4 -ss 00:00:10 -t 00:00:05 test_clips/clip1.mp4
ffmpeg -i video_longo.mp4 -ss 00:01:30 -t 00:00:08 test_clips/clip2.mp4
```

### 2. Indexar Clips

```bash
# Indexar cada clip
python simple_curator.py index test_clips/clip1.mp4 clip_001
python simple_curator.py index test_clips/clip2.mp4 clip_002
python simple_curator.py index test_clips/clip3.mp4 clip_003

# Loop para indexar todos
for file in test_clips/*.mp4; do
    id=$(basename "$file" .mp4)
    python simple_curator.py index "$file" "$id"
done
```

### 3. Buscar Clips

```bash
# Busca semântica
python simple_curator.py search "skate fail engraçado"
python simple_curator.py search "momento épico esportes"
python simple_curator.py search "animais fofos"
```

### Exemplo de Output

```
🔍 Buscando: 'skate fail engraçado'
  Encontrados 5 resultados

1. [0.892] Skatista tenta manobra complexa e cai de forma cômica
   Emoção: cômico, Viral: 8.5
   Tags: skate, fail, comédia

2. [0.834] Pessoa perde equilíbrio em rampa e público reage
   Emoção: cômico, Viral: 7.0
   Tags: skate, queda, público

3. [0.781] Tentativa de flip que dá errado de forma inesperada
   Emoção: cômico, Viral: 8.0
   Tags: skate, surpresa, fail

✅ Concluído!
```

---

## 📊 Validando Resultados

### Script de Análise

```python
# analyze_collection.py

from qdrant_client import QdrantClient

db = QdrantClient(url="http://localhost:6333")

# Obter todos os clips
results = db.scroll(collection_name="clips", limit=100)

clips = results[0]

print(f"Total de clips: {len(clips)}")
print("\nDistribuição de emoções:")

emotions = {}
for clip in clips:
    emotion = clip.payload["emotion"]
    emotions[emotion] = emotions.get(emotion, 0) + 1

for emotion, count in sorted(emotions.items(), key=lambda x: -x[1]):
    print(f"  {emotion}: {count}")

print("\nTop 5 clips por viral score:")
sorted_clips = sorted(clips, key=lambda c: c.payload["viral_score"], reverse=True)

for clip in sorted_clips[:5]:
    print(f"  [{clip.payload['viral_score']}] {clip.payload['description'][:60]}...")
```

---

## 🎓 Próximos Passos

### Melhorias Incrementais

**Curto Prazo (1-2 semanas)**
1. Adicionar mais frames (8 ao invés de 4)
2. Prompt mais detalhado para Claude
3. Filtros por emoção/intensidade na busca
4. Cache de análises (evitar reprocessar)

**Médio Prazo (1 mês)**
1. Interface web simples (Streamlit/Gradio)
2. Batch processing (indexar 100+ clips automaticamente)
3. Análise de áudio (Whisper)
4. PostgreSQL para metadata

**Longo Prazo (3 meses)**
1. Sistema completo com LangGraph
2. Renderização automática
3. API REST
4. Pipeline CI/CD

---

## 🐛 Troubleshooting Comum

### Erro: "No module named 'scenedetect'"

```bash
pip install scenedetect[opencv]
```

### Erro: "CUDA out of memory"

```python
# Em SimpleEmbedder.__init__:
self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
# Adicionar:
self.model = self.model.to("cpu")  # Forçar CPU
```

### Erro: "Qdrant connection refused"

```bash
# Verificar se Qdrant está rodando
docker ps | grep qdrant

# Se não estiver:
docker run -d -p 6333:6333 qdrant/qdrant
```

### Erro: "Rate limit exceeded" (Anthropic)

```python
# Adicionar delay entre chamadas
import time

def analyze_with_claude(frames):
    # ... código existente ...
    time.sleep(2)  # 2 segundos entre requests
```

---

## 💰 Custos Esperados (Teste)

### Indexação de 10 Clips

- Claude API (10 clips × $0.003): **$0.03**
- Qdrant (grátis no free tier): **$0**
- CLIP (local, grátis): **$0**

**Total: ~$0.03**

### Indexação de 1000 Clips

- Claude API (1000 clips × $0.003): **$3.00**
- Qdrant Cloud (free até 1M vetores): **$0**
- Storage (assumindo S3): **~$1.00**

**Total: ~$4.00**

---

## ✅ Checklist de Sucesso

Você está pronto para avançar quando conseguir:

- [x] Indexar 10+ clips sem erros
- [x] Buscar por tema e obter resultados relevantes
- [x] Analisar distribuição de emoções/scores
- [x] Embeddings sendo gerados corretamente
- [x] Qdrant salvando e recuperando dados

**Próximo nível**: Integrar com LangGraph para produção automática!

---

## 📚 Recursos Adicionais

- [Documentação Anthropic](https://docs.anthropic.com)
- [Qdrant Docs](https://qdrant.tech/documentation/)
- [CLIP Paper](https://arxiv.org/abs/2103.00020)
- [LangGraph Tutorial](https://langchain-ai.github.io/langgraph/)

---

**Dúvidas?** Abra uma issue no repositório ou consulte a documentação completa em `/docs`.
