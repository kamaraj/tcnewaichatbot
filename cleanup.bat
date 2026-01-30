@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo    TCA AI Chatbot - Environment Cleanup
echo ==========================================
echo.

:: Ask for confirmation
set /p confirm="Are you sure you want to delete all uploaded files, vector databases, and logs? (y/n): "
if /i "%confirm%" neq "y" (
    echo Cleanup cancelled.
    exit /b
)

echo.
echo [1/5] Deleting uploaded documents...
if exist "uploads" (
    del /s /q "uploads\*.*"
    echo    - Uploads cleared.
)

echo [2/5] Deleting vector database (ChromaDB)...
if exist "chroma_db" (
    rmdir /s /q "chroma_db"
    echo    - ChromaDB deleted.
)

echo [3/5] Deleting log files and reports...
set "files_to_delete=debug_output.txt eval_report.json .coverage *.log"
for %%f in (%files_to_delete%) do (
    if exist "%%f" (
        del /q "%%f"
        echo    - Deleted %%f
    )
)

echo [4/5] Cleaning up Python cache and temporary files...
:: Delete __pycache__ directories recursively
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d"
    )
)
:: Delete .pytest_cache
if exist ".pytest_cache" rmdir /s /q ".pytest_cache"
:: Delete .ipynb_checkpoints
for /d /r . %%d in (.ipynb_checkpoints) do (
    if exist "%%d" (
        rd /s /q "%%d"
    )
)
:: Delete compiled python files
del /s /q *.pyc *.pyo *.pyd >nul 2>&1
echo    - Python cache and temp files cleared.

echo [5/5] Checking for other artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
for /d /r . %%d in (*.egg-info) do if exist "%%d" rd /s /q "%%d"
echo    - Build artifacts cleared.

echo.
echo ==========================================
echo        Cleanup Completed Successfully!
echo ==========================================
echo.
pause
