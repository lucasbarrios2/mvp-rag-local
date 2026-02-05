# Sistema Multi-Agente de Produção de Vídeos Compilados
**Versão Base - Janeiro 2026**

## Arquitetura Geral

```
Usuário: "Quero um vídeo sobre 'fails épicos de skate'"
    ↓
[COORDENADOR] → orquestra todo o pipeline
    ↓
[CURADOR] → seleciona clips do banco de dados
    ↓
[EDITOR] → define ordem, transições, música
    ↓
[QA] → valida qualidade, direitos, duração
    ↓
[METADADOS] → gera título, descrição, tags, thumbnail
    ↓
[RENDERIZADOR] → produz vídeo final
    ↓
Vídeo pronto para upload!
```

## Estado Compartilhado

```python
from typing import TypedDict, Annotated, Literal
from operator import add
from dataclasses import dataclass

@dataclass
class VideoClip:
    """Representa um clip do banco de dados"""
    id: str
    file_path: str
    duration: float
    tags: list[str]
    category: str
    quality_score: float
    engagement_rate: float
    rights_cleared: bool
    metadata: dict

class VideoProductionState(TypedDict):
    # Input do usuário
    theme: str
    target_duration: int
    style: Literal["energetic", "chill", "emotional"]

    # Memória de trabalho
    selected_clips: Annotated[list[VideoClip], add]
    rejected_clips: Annotated[list[str], add]

    # Decisões dos agentes
    clip_order: list[str]
    transitions: list[str]
    background_music: str

    # Metadados
    title: str
    description: str
    tags: list[str]
    thumbnail_timestamp: float

    # Controle de qualidade
    qa_approved: bool
    qa_issues: Annotated[list[str], add]

    # Status
    status: Literal["curating", "editing", "qa", "metadata", "rendering", "done"]
    current_agent: str

    # Output
    final_video_path: str
    estimated_views: int
```

## Implementação Completa

[Ver código Python completo dos agentes no contexto anterior]

## Limitações Atuais

1. **Seleção Básica**: Tags simples, sem compreensão semântica profunda
2. **Sem Análise Visual**: Não analisa o conteúdo visual dos clips
3. **Busca por Keywords**: Depende de metadata manual
4. **Sem Contexto Narrativo**: Não entende "arco dramático" entre clips
5. **Dados Estruturados Apenas**: Requer metadados pré-definidos

## Próximos Passos

- Implementar RAG multimodal
- Integrar análise de vídeo com LLMs
- Sistema de embeddings para busca semântica
- Pipeline de análise automatizada de clips
