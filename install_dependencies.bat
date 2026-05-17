@echo off
REM ============================================================================
REM Script de Instalacao de Dependencias - API JIRA + AWS
REM ============================================================================
REM Este script baixa e instala automaticamente todas as bibliotecas
REM essenciais do projeto (Jira, dotenv, pydantic, pandas, boto3)
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo Instalador de Dependencias - API JIRA + AWS
echo ============================================================================
echo.

REM Verifica se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH!
    echo Por favor, instale Python e adicione-o ao PATH do sistema.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version
echo.

REM Atualiza pip para a versao mais recente
echo [*] Atualizando pip...
python -m pip install --upgrade pip
echo.

REM Lista de bibliotecas a instalar
echo [*] Instalando bibliotecas essenciais do projeto...
echo.

python -m pip install requests python-dotenv pydantic pandas boto3

echo.
echo ============================================================================
echo [SUCESSO] Todas as bibliotecas foram instaladas com sucesso!
echo ============================================================================
echo.
echo Bibliotecas instaladas:
echo   - requests           (chamadas HTTP para API Jira)
echo   - python-dotenv      (gerenciamento de variaveis de ambiente)
echo   - pydantic           (validacao de modelos de dados)
echo   - pandas             (manipulacao e processamento de dados)
echo   - boto3              (integracao com AWS S3 e Lambda)
echo.
echo [IMPORTANTE] Estas sao as dependencias REAIS do projeto.
echo              Se necessitar libs adicionais (Data Science/ML),
echo              execute em separado ou adicione ao requirements.txt
echo.
pause
exit /b 0
