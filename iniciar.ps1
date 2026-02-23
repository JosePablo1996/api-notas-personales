# iniciar.ps1
Write-Host "🚀 Iniciando API de Notas" -ForegroundColor Green
cd C:\Proyectos_Apis\api-notas-personales
venv\Scripts\activate
uvicorn app.main:app --reload