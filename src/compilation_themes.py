"""
Taxonomia de temas para compilados estilo Refugio Mental.
28 temas organizados em 6 categorias.
"""

COMPILATION_THEMES: dict[str, str] = {
    # Animais (8)
    "animais_em_cidades": "Animais selvagens em areas urbanas, ruas, lojas, casas",
    "animais_estrada": "Animais cruzando estradas, rodovias, flagras em dashcam",
    "animais_vs_humanos": "Confrontos ou interacoes inusitadas entre animais e pessoas",
    "animais_salvamentos": "Resgates de animais em perigo, operacoes de salvamento",
    "animais_comportamento": "Comportamento animal surpreendente, inteligencia, habilidades",
    "animais_domesticos_loucos": "Pets fazendo coisas absurdas, engracadas ou inesperadas",
    "animais_predadores": "Predadores em acao, caca, emboscadas, confrontos entre animais",
    "animais_marinhos": "Vida marinha, baleias, tubaroes, criaturas do oceano",
    # Natureza (4)
    "desastres_naturais": "Terremotos, erupcoes, tsunamis, deslizamentos, enchentes",
    "clima_extremo": "Tempestades, tornados, granizo, nevascas, raios",
    "fenomenos_naturais": "Aurora boreal, eclipses, nuvens raras, fenomenos opticos",
    "paisagens_impressionantes": "Paisagens de tirar o folego, natureza exuberante",
    # Transito (4)
    "acidentes_transito": "Acidentes de carro, moto, caminhao capturados em camera",
    "manobras_impossiveis": "Manobras arriscadas, ultrapassagens, desvios impressionantes",
    "flagras_dashcam": "Flagras gerais capturados por cameras veiculares",
    "perseguicoes": "Perseguicoes policiais, fugas, corridas em via publica",
    # Flagras (4)
    "flagras_cctv": "Flagras capturados por cameras de seguranca",
    "flagras_inacreditaveis": "Situacoes absurdas e inacreditaveis flagradas em video",
    "quase_acidentes": "Near-misses, escapes por centimetros, sorte extrema",
    "karma_instantaneo": "Karma instantaneo, justica poetica capturada em video",
    # Pessoas (5)
    "fails_epicos": "Falhas espetaculares, tombos, tentativas que deram errado",
    "habilidades_incriveis": "Habilidades humanas impressionantes, talentos excepcionais",
    "herois_anonimos": "Atos heroicos de pessoas comuns, salvamentos, coragem",
    "momentos_wholesome": "Momentos emocionantes, reencontros, gentileza, emocao",
    "trabalho_perigoso": "Trabalhos arriscados, situacoes perigosas no trabalho",
    # Misterio (3)
    "misterios_inexplicaveis": "Eventos misteriosos, inexplicados, bizarros",
    "lugares_abandonados": "Exploracao de locais abandonados, ruinas, lugares esquecidos",
    "coincidencias_absurdas": "Coincidencias improvaveis, timing perfeito, sincronia absurda",
}

VALID_THEME_CODES: set[str] = set(COMPILATION_THEMES.keys())

COMPILATION_THEMES_TAXONOMY_TEXT: str = "\n".join(
    f"- {code}: {description}" for code, description in COMPILATION_THEMES.items()
)
