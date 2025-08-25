#!/bin/bash

# Скрипт проверки готовности проекта к развертыванию
# Использование: ./check-deployment.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

ERRORS=0
WARNINGS=0

check_file() {
    if [[ -f "$1" ]]; then
        log_success "Файл найден: $1"
    else
        log_error "Файл отсутствует: $1"
        ERRORS=$((ERRORS + 1))
    fi
}

check_executable() {
    if [[ -x "$1" ]]; then
        log_success "Скрипт исполняемый: $1"
    else
        log_error "Скрипт не исполняемый: $1"
        ERRORS=$((ERRORS + 1))
    fi
}

log_info "🔍 Проверка готовности проекта к развертыванию..."

echo
log_info "📁 Проверка структуры проекта:"
check_file "app/main.py"
check_file "requirements.txt"
check_file "frontend/frontend-necrasovka/package.json"
check_file "frontend/frontend-necrasovka/src/App.jsx"

echo
log_info "🐳 Проверка Docker файлов:"
check_file "Dockerfile.backend"
check_file "Dockerfile.frontend"
check_file "docker-compose.prod.yml"
check_file ".dockerignore"
check_file "deploy/nginx.conf"

echo
log_info "⚙️ Проверка конфигурации:"
check_file "env.prod.template"

if [[ -f ".env" ]]; then
    log_success "Локальный .env найден"
else
    log_warning "Локальный .env не найден (нормально для деплоя)"
fi

echo
log_info "📜 Проверка скриптов развертывания:"
check_executable "deploy/deploy.sh"
check_executable "deploy/update.sh"
check_executable "deploy/sync-to-server.sh"
check_executable "deploy/monitor.sh"
check_executable "deploy/setup-monitoring.sh"
check_executable "deploy/full-deploy.sh"
check_executable "deploy/fix-and-deploy.sh"

echo
log_info "📚 Проверка документации:"
check_file "DEPLOYMENT.md"
check_file "QUICK_START.md"
check_file "DEPLOYMENT_FIXES.md"
check_file "DEPLOYMENT_SUMMARY.md"

echo
log_info "🔧 Проверка зависимостей Python:"
if python -c "import fastapi, uvicorn, opensearchpy" 2>/dev/null; then
    log_success "Python зависимости доступны"
else
    log_warning "Python зависимости не установлены (нормально если используется venv)"
fi

echo
log_info "📦 Проверка зависимостей Node.js:"
if [[ -d "frontend/frontend-necrasovka/node_modules" ]]; then
    log_success "Node.js зависимости установлены"
else
    log_warning "Node.js зависимости не установлены"
    WARNINGS=$((WARNINGS + 1))
fi

echo
log_info "🔍 Проверка Docker (если доступен):"
if command -v docker &> /dev/null; then
    if docker --version &> /dev/null; then
        log_success "Docker доступен"
    else
        log_warning "Docker не запущен"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_warning "Docker не установлен (будет установлен на сервере)"
fi

echo
log_info "🌐 Проверка сетевых утилит:"
if command -v curl &> /dev/null; then
    log_success "curl доступен"
else
    log_error "curl не установлен"
    ERRORS=$((ERRORS + 1))
fi

if command -v rsync &> /dev/null; then
    log_success "rsync доступен"
else
    log_error "rsync не установлен (нужен для синхронизации)"
    ERRORS=$((ERRORS + 1))
fi

if command -v ssh &> /dev/null; then
    log_success "ssh доступен"
else
    log_error "ssh не установлен (нужен для подключения к серверу)"
    ERRORS=$((ERRORS + 1))
fi

echo
log_info "📊 Результаты проверки:"
echo "  Ошибки: $ERRORS"
echo "  Предупреждения: $WARNINGS"

echo
if [[ $ERRORS -eq 0 ]]; then
    log_success "✅ Проект готов к развертыванию!"
    echo
    log_info "🚀 Для развертывания выполните:"
    log_info "  ./deploy/full-deploy.sh 89.169.3.47 root"
    echo
    log_info "📋 Или пошагово:"
    log_info "  1. ./deploy/sync-to-server.sh 89.169.3.47 root"
    log_info "  2. ssh root@89.169.3.47"
    log_info "  3. cd /opt/necrasovka && cp env.prod.template .env.prod"
    log_info "  4. nano .env.prod  # Заполнить реальными значениями"
    log_info "  5. ./deploy/deploy.sh"
    exit 0
else
    log_error "❌ Найдены критические ошибки. Исправьте их перед развертыванием."
    exit 1
fi
