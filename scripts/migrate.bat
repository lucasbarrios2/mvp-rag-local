@echo off
REM ============================================================================
REM Migração do Banco de Dados - MVP RAG Local
REM ============================================================================

echo.
echo ========================================
echo  Migracao do Banco de Dados
echo ========================================
echo.

REM Verificar se PostgreSQL está rodando
echo Verificando se PostgreSQL esta rodando...
docker ps | findstr video-curator-postgres >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Container PostgreSQL nao esta rodando.
    echo Execute primeiro: cd docker ^&^& docker-compose up -d
    pause
    exit /b 1
)
echo [OK] PostgreSQL esta rodando

echo.
echo Executando migracao...
echo.

REM Executar migração
docker exec -i video-curator-postgres psql -U curator -d video_assets < database\migrations\001_migration_extend_schema.sql

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Migracao falhou!
    echo Verifique os logs acima.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Migracao Concluida com Sucesso!
echo ========================================
echo.
echo Novos campos adicionados ao schema:
echo - scene_description
echo - emotional_tone
echo - intensity, surprise_factor, viral_potential
echo - visual_elements (JSONB)
echo - theme_scores (JSONB)
echo - embedding_id
echo - E mais 20+ campos...
echo.
echo Seus dados existentes foram PRESERVADOS!
echo.
echo Proximo passo:
echo - Enriquecer clips: python src\pipeline\enrichment_pipeline.py
echo.
pause
