@echo off
REM ============================================================================
REM Stop Services - MVP RAG Local
REM ============================================================================

echo.
echo ========================================
echo  Parando Servicos Docker
echo ========================================
echo.

cd docker

docker-compose stop

echo.
echo [OK] Servicos parados.
echo.
echo Para remover containers completamente:
echo   cd docker ^&^& docker-compose down
echo.
echo Para remover containers E volumes (CUIDADO: perde dados):
echo   cd docker ^&^& docker-compose down -v
echo.
pause
