@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 goto missing
  set "PY=python"
)
%PY% -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if errorlevel 1 goto missing
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto failed
%PY% main.py
if errorlevel 1 goto failed
%PY% -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo.
echo DONE. Upload results/, docs/, Lab2_Report.docx to GitHub.
pause
exit /b 0
:missing
echo ERROR: Python 3.10 or newer required. See README.md.
pause
exit /b 1
:failed
echo ERROR: Check the traceback above and README.md.
pause
exit /b 1
