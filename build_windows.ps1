$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m pytest

python -m PyInstaller --noconfirm --clean --onedir --console --name CollegeAIAssistant --paths src --collect-all playwright --collect-all pymupdf --collect-submodules docx --collect-submodules pptx src/college_assistant/main.py
@'
@echo off
cd /d "%~dp0"
start "" "%~dp0CollegeAIAssistant.exe"
'@ | Set-Content -Encoding ascii "dist/CollegeAIAssistant/Start College AI Assistant.bat"
Compress-Archive -Path "dist/CollegeAIAssistant" -DestinationPath "CollegeAIAssistant-Windows.zip" -Force
Write-Host "Package created: $Root\CollegeAIAssistant-Windows.zip"
