<#
.SYNOPSIS
    Script de inicio para la API de Notas Personales v1.1.0
.DESCRIPTION
    Este script automatiza el inicio de la API de Notas Personales,
    verificando el entorno virtual, las dependencias y configuraciones necesarias.
.NOTES
    Autor: Jose Pablo Miranda Quintanilla
    Versión: 1.1.0
    Fecha: 2026-02-27
    Requisitos: Python 3.8+, PostgreSQL, VirtualEnv
.LINK
    Documentación: http://localhost:8000/docs
.EXAMPLE
    .\iniciar.ps1
    Inicia la API con la configuración por defecto
.EXAMPLE
    .\iniciar.ps1 -Port 8080 -Host "0.0.0.0"
    Inicia la API en el puerto 8080 accesible desde cualquier interfaz
#>

param(
    [Parameter(Mandatory=$false, HelpMessage="Puerto para la API (default: 8000)")]
    [int]$Port = 8000,
    
    [Parameter(Mandatory=$false, HelpMessage="Host para la API (default: 127.0.0.1)")]
    [string]$Host = "127.0.0.1",
    
    [Parameter(Mandatory=$false, HelpMessage="Entorno (development/production)")]
    [ValidateSet("development", "production")]
    [string]$Environment = "development",
    
    [Parameter(Mandatory=$false, HelpMessage="Nivel de log (DEBUG/INFO/WARNING/ERROR)")]
    [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR")]
    [string]$LogLevel = "INFO",
    
    [Parameter(Mandatory=$false, HelpMessage="Saltar verificación de dependencias")]
    [switch]$SkipChecks
)

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================

# Colores para output
$Colors = @{
    Info = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Header = "Magenta"
}

# Rutas del proyecto
$ProjectPath = "C:\Proyectos_Apis\api-notas-personales"
$VenvPath = "$ProjectPath\venv"
$RequirementsFile = "$ProjectPath\requirements.txt"
$EnvFile = "$ProjectPath\.env"

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White",
        [string]$Prefix = ""
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $prefixColor = switch ($Prefix) {
        "INFO" { $Colors.Info }
        "SUCCESS" { $Colors.Success }
        "WARNING" { $Colors.Warning }
        "ERROR" { $Colors.Error }
        default { "White" }
    }
    
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
    if ($Prefix) {
        Write-Host "[$Prefix] " -NoNewline -ForegroundColor $prefixColor
    }
    Write-Host $Message -ForegroundColor $Color
}

function Show-Banner {
    Clear-Host
    Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🚀 API DE NOTAS PERSONALES v1.1.0                       ║
║                                                              ║
║     Iniciando servidor FastAPI con PostgreSQL                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor $Colors.Header
    Write-Host ""
}

function Test-Requirements {
    Write-ColorOutput "Verificando requisitos del sistema..." -Color $Colors.Info -Prefix "INFO"
    
    # Verificar Python
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = $matches[1]
            $minor = $matches[2]
            if (($major -ge 3) -and ($minor -ge 8)) {
                Write-ColorOutput "✓ Python $major.$minor+ detectado" -Color $Colors.Success -Prefix "SUCCESS"
            } else {
                Write-ColorOutput "✗ Python 3.8+ requerido (versión actual: $major.$minor)" -Color $Colors.Error -Prefix "ERROR"
                return $false
            }
        } else {
            Write-ColorOutput "✗ No se pudo determinar la versión de Python" -Color $Colors.Error -Prefix "ERROR"
            return $false
        }
    } catch {
        Write-ColorOutput "✗ Python no está instalado o no está en el PATH" -Color $Colors.Error -Prefix "ERROR"
        return $false
    }
    
    # Verificar entorno virtual
    if (Test-Path $VenvPath) {
        Write-ColorOutput "✓ Entorno virtual encontrado" -Color $Colors.Success -Prefix "SUCCESS"
    } else {
        Write-ColorOutput "✗ Entorno virtual no encontrado en: $VenvPath" -Color $Colors.Error -Prefix "ERROR"
        Write-ColorOutput "  Ejecuta: python -m venv venv" -Color $Colors.Warning -Prefix "WARNING"
        return $false
    }
    
    # Verificar archivo .env
    if (Test-Path $EnvFile) {
        Write-ColorOutput "✓ Archivo .env encontrado" -Color $Colors.Success -Prefix "SUCCESS"
    } else {
        Write-ColorOutput "⚠ Archivo .env no encontrado" -Color $Colors.Warning -Prefix "WARNING"
        Write-ColorOutput "  Usando variables de entorno por defecto" -Color $Colors.Warning
    }
    
    # Verificar requirements.txt
    if (Test-Path $RequirementsFile) {
        Write-ColorOutput "✓ Archivo requirements.txt encontrado" -Color $Colors.Success -Prefix "SUCCESS"
    } else {
        Write-ColorOutput "✗ requirements.txt no encontrado" -Color $Colors.Error -Prefix "ERROR"
        return $false
    }
    
    return $true
}

function Install-Dependencies {
    Write-ColorOutput "Verificando dependencias..." -Color $Colors.Info -Prefix "INFO"
    
    # Activar entorno virtual
    & "$VenvPath\Scripts\Activate.ps1"
    
    # Verificar e instalar dependencias
    $outdated = pip list --outdated
    if ($outdated.Count -gt 2) { # Más allá de los headers
        Write-ColorOutput "Hay dependencias desactualizadas" -Color $Colors.Warning -Prefix "WARNING"
        $response = Read-Host "¿Deseas actualizar todas las dependencias? (s/N)"
        if ($response -eq 's') {
            pip install --upgrade -r $RequirementsFile
        }
    } else {
        pip install -r $RequirementsFile
    }
    
    Write-ColorOutput "✓ Dependencias verificadas" -Color $Colors.Success -Prefix "SUCCESS"
}

function Show-Configuration {
    Write-ColorOutput "Configuración actual:" -Color $Colors.Info -Prefix "INFO"
    Write-Host "  • Puerto    : " -NoNewline
    Write-Host $Port -ForegroundColor Yellow
    Write-Host "  • Host      : " -NoNewline
    Write-Host $Host -ForegroundColor Yellow
    Write-Host "  • Entorno   : " -NoNewline
    Write-Host $Environment -ForegroundColor Yellow
    Write-Host "  • Log Level : " -NoNewline
    Write-Host $LogLevel -ForegroundColor Yellow
    Write-Host "  • Proyecto  : " -NoNewline
    Write-Host $ProjectPath -ForegroundColor Yellow
    Write-Host ""
}

function Start-APIServer {
    Write-ColorOutput "Iniciando servidor API..." -Color $Colors.Info -Prefix "INFO"
    
    # Construir comando uvicorn
    $uvicornCmd = "uvicorn app.main:app"
    $uvicornArgs = @(
        "--host", $Host,
        "--port", $Port,
        "--reload"  # Solo funciona en development
    )
    
    # Configuración adicional según entorno
    if ($Environment -eq "production") {
        $uvicornArgs = @(
            "--host", $Host,
            "--port", $Port,
            "--workers", "4",
            "--log-level", $LogLevel.ToLower()
        )
        Write-ColorOutput "🔒 Modo producción: workers=4" -Color $Colors.Warning -Prefix "WARNING"
    } else {
        Write-ColorOutput "🔧 Modo desarrollo: reload activado" -Color $Colors.Info -Prefix "INFO"
    }
    
    # Establecer variable de entorno
    $env:ENVIRONMENT = $Environment
    $env:LOG_LEVEL = $LogLevel
    
    Write-ColorOutput "📡 Servidor disponible en:" -Color $Colors.Info -Prefix "INFO"
    Write-Host "  • Local:    http://localhost:$Port" -ForegroundColor Green
    Write-Host "  • Red:      http://$($Host):$Port" -ForegroundColor Green
    Write-Host "  • Docs:     http://localhost:$Port/docs" -ForegroundColor Cyan
    Write-Host "  • ReDoc:    http://localhost:$Port/redoc" -ForegroundColor Cyan
    Write-Host "  • OpenAPI:  http://localhost:$Port/openapi.json" -ForegroundColor Cyan
    Write-Host ""
    Write-ColorOutput "Presiona Ctrl+C para detener el servidor" -Color $Colors.Warning -Prefix "INFO"
    Write-Host ""
    
    # Ejecutar uvicorn
    & "$VenvPath\Scripts\uvicorn" app.main:app @uvicornArgs
}

# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================

try {
    # Mostrar banner
    Show-Banner
    
    # Mostrar configuración
    Show-Configuration
    
    # Cambiar al directorio del proyecto
    Set-Location $ProjectPath
    
    # Verificar requisitos (si no se salta)
    if (-not $SkipChecks) {
        $checksPassed = Test-Requirements
        if (-not $checksPassed) {
            Write-ColorOutput "❌ No se puede iniciar la API - Requisitos no cumplidos" -Color $Colors.Error -Prefix "ERROR"
            exit 1
        }
    }
    
    # Instalar/verificar dependencias
    Install-Dependencies
    
    # Iniciar servidor
    Start-APIServer
    
} catch {
    Write-ColorOutput "❌ Error inesperado: $_" -Color $Colors.Error -Prefix "ERROR"
    Write-Host "Detalles del error:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    exit 1
} finally {
    Write-ColorOutput "🛑 Servidor detenido" -Color $Colors.Warning -Prefix "INFO"
}