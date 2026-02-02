@echo off
REM ============================================================================
REM Setup Script - MVP RAG Local (Windows)
REM ============================================================================

echo.
echo ========================================
echo  MVP RAG Local - Setup Inicial
echo ========================================
echo.

REM Verificar se Docker esta rodando
echo [1/5] Verificando Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao encontrado. Instale Docker Desktop primeiro.
    echo Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker encontrado

REM Verificar se Python esta instalado
echo.
echo [2/5] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale Python 3.10+ primeiro.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python encontrado

REM Criar .env se nao existir
echo.
echo [3/5] Configurando variaveis de ambiente...
if not exist ".env" (
    copy ".env.example" ".env"
    echo [ATENCAO] Arquivo .env criado a partir do .env.example
    echo IMPORTANTE: Edite .env e adicione sua GOOGLE_API_KEY
    notepad ".env"
) else (
    echo [OK] Arquivo .env ja existe
)

REM Criar ambiente virtual Python
echo.
echo [4/5] Criando ambiente virtual Python...
if not exist "venv\" (
    python -m venv venv
    echo [OK] Ambiente virtual criado
) else (
    echo [OK] Ambiente virtual ja existe
)

REM Ativar venv e instalar dependencias
echo.
echo [5/5] Instalando dependencias Python...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Dependencias instaladas

REM Criar diretorio de uploads
if not exist "uploads\" mkdir uploads

echo.
echo ========================================
echo  Setup Concluido!
echo ========================================
echo.
echo Proximos passos:
echo.
echo 1. Edite .env e adicione sua GOOGLE_API_KEY
echo    (se ainda nao fez)
echo.
echo 2. Suba a infraestrutura Docker:
echo    scripts\start.bat
echo.
echo 3. Rode a interface Streamlit:
echo    venv\Scripts\activate
echo    streamlit run app.py
echo.
pause
