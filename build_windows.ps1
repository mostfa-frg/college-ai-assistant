$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .

$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $Root ".playwright-browsers"
python -m playwright install chromium

python -m PyInstaller --noconfirm --clean --onedir --console --name CollegeAIAssistant --paths src --collect-all playwright --collect-all pymupdf --collect-all docx --collect-all pptx src/college_assistant/main.py
Copy-Item -Recurse -Force ".playwright-browsers" "dist/CollegeAIAssistant/_playwright-browsers"
@'
@echo off
cd /d "%~dp0"
start "" "%~dp0CollegeAIAssistant.exe"
'@ | Set-Content -Encoding ascii "dist/CollegeAIAssistant/Start College AI Assistant.bat"
Compress-Archive -Path "dist/CollegeAIAssistant" -DestinationPath "CollegeAIAssistant-Windows.zip" -Force
Write-Host "Package created: $Root\CollegeAIAssistant-Windows.zip"
