# Jarvis Desktop Pet - Setup Script (Windows)
Write-Host "Creating virtual environment..."
python -m venv .venv
.venv\Scripts\Activate.ps1
Write-Host "Installing requirements..."
pip install -U pip
pip install -r requirements.txt
Write-Host "Setup complete. Start LM Studio with the recommended models."
