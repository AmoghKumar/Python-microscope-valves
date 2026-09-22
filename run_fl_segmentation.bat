@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "CONDA_ROOT=C:\ProgramData\anaconda3"
set "ENV_NAME=chemostat_sam2"

call "%CONDA_ROOT%\condabin\conda.bat" activate %ENV_NAME%
if errorlevel 1 (
    echo Failed to activate conda environment "%ENV_NAME%".
    pause
    exit /b 1
)

cd /d "%SCRIPT_DIR%"
python fl_segmentation_Newchip.py

echo.
echo fl_segmentation_Newchip.py has exited.
pause
