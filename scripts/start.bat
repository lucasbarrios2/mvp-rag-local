@echo off
REM ============================================================================
REM Start Services - MVP RAG Local
REM ============================================================================

echo.
echo ========================================
echo  Iniciando Servicos Docker
echo ========================================
echo.

cd docker

echo Subindo containers...
docker-compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao subir containers!
    pause
    exit /b 1
)

echo.
echo Aguardando servicos iniciarem...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo  Status dos Servicos
echo ========================================
echo.

docker-compose ps

echo.
echo ========================================
echo  Servicos Disponiveis
echo ========================================
echo.
echo PostgreSQL:  localhost:5432
echo   Usuario: curator
echo   Banco: video_assets
echo.
echo Qdrant:      http://localhost:6333
echo   Dashboard: http://localhost:6333/dashboard
echo.
echo ========================================
echo.
echo Para iniciar a interface:
echo   streamlit run app.py
echo.
echo Para ver logs em tempo real:
echo   cd docker ^&^& docker-compose logs -f
echo.
echo Para parar os servicos:
echo   scripts\stop.bat
echo.
pause
