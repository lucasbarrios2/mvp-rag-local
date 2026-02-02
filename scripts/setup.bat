@echo off
REM ============================================================================
REM Setup Script - MVP RAG Local (Windows)
REM ============================================================================

echo.
echo ========================================
echo  MVP RAG Local - Setup Inicial
echo ========================================
echo.

REM Verificar se Docker está rodando
echo [1/6] Verificando Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao encontrado. Instale Docker Desktop primeiro.
    echo Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker encontrado

REM Verificar se Python está instalado
echo.
echo [2/6] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale Python 3.10+ primeiro.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python encontrado

REM Criar .env se não existir
echo.
echo [3/6] Configurando variaveis de ambiente...
if not exist "docker\.env" (
    copy "docker\.env.example" "docker\.env"
    echo [ATENCAO] Arquivo docker\.env criado a partir do .env.example
    echo IMPORTANTE: Edite docker\.env e adicione sua ANTHROPIC_API_KEY
    notepad "docker\.env"
) else (
    echo [OK] Arquivo .env ja existe
)

REM Criar ambiente virtual Python
echo.
echo [4/6] Criando ambiente virtual Python...
if not exist "venv\" (
    python -m venv venv
    echo [OK] Ambiente virtual criado
) else (
    echo [OK] Ambiente virtual ja existe
)

REM Ativar venv e instalar dependências
echo.
echo [5/6] Instalando dependencias Python...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Dependencias instaladas

REM Criar diretórios de dados
echo.
echo [6/6] Criando diretorios de dados...
if not exist "data\" mkdir data
if not exist "data\frames_cache\" mkdir data\frames_cache
if not exist "data\videos\" mkdir data\videos
echo [OK] Diretorios criados

echo.
echo ========================================
echo  Setup Concluido!
echo ========================================
echo.
echo Proximos passos:
echo.
echo 1. Edite docker\.env e adicione sua ANTHROPIC_API_KEY
echo    (se ainda nao fez)
echo.
echo 2. Suba a infraestrutura Docker:
echo    cd docker
echo    docker-compose up -d
echo.
echo 3. Rode a migracao do banco de dados:
echo    scripts\migrate.bat
echo.
echo 4. Enriqueça seus primeiros clips:
echo    venv\Scripts\activate
echo    python src\pipeline\enrichment_pipeline.py
echo.
echo Para mais detalhes, leia: docs\00_SETUP_GUIDE.md
echo.
pause
