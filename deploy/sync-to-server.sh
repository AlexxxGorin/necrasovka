#!/bin/bash

# Скрипт синхронизации проекта с сервером
# Использование: ./sync-to-server.sh [SERVER_IP] [SERVER_USER]

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
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Параметры сервера
SERVER_IP=${1:-"89.169.3.47"}
SERVER_USER=${2:-"root"}
PROJECT_DIR="/opt/necrasovka"

log_info "🚀 Синхронизация проекта с сервером $SERVER_USER@$SERVER_IP..."

# Проверка подключения к серверу
if ! ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER_IP "echo 'Connection test'" >/dev/null 2>&1; then
    log_error "Не удается подключиться к серверу $SERVER_USER@$SERVER_IP"
    log_error "Проверьте:"
    log_error "  1. IP адрес сервера"
    log_error "  2. SSH ключи или пароль"
    log_error "  3. Доступность сервера"
    exit 1
fi

log_success "Подключение к серверу установлено"

# Создание директории на сервере
log_info "Создание рабочей директории на сервере..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"

# Список файлов для синхронизации
log_info "Подготовка файлов для синхронизации..."

# Создаем временный файл со списком исключений
cat > /tmp/rsync-exclude << EOF
.git/
.gitignore
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
node_modules/
.npm/
.cache/
.DS_Store
.vscode/
.idea/
*.log
logs/*.log
.env
.env.local
frontend/frontend-necrasovka/dist/
frontend/frontend-necrasovka/node_modules/
test_search_modes.py
analyze_query.py
compare_search_versions.py
run_tests.py
monitor_search_quality.py
search_quality_history.json
SEARCH_TESTING.md
SEARCH_MODES.md
EOF

# Синхронизация файлов
log_info "Синхронизация файлов..."
rsync -avz --progress \
    --exclude-from=/tmp/rsync-exclude \
    --delete \
    ./ $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

# Удаление временного файла
rm /tmp/rsync-exclude

log_success "Файлы синхронизированы"

# Создание .env.prod на сервере (если не существует)
log_info "Проверка конфигурации на сервере..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && if [ ! -f .env.prod ]; then cp env.prod.template .env.prod; echo 'Создан файл .env.prod из шаблона'; fi"

# Установка прав на скрипты
log_info "Установка прав на скрипты..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && chmod +x deploy/*.sh"

log_success "✅ Синхронизация завершена!"

log_info "Следующие шаги:"
log_info "  1. Подключитесь к серверу: ssh $SERVER_USER@$SERVER_IP"
log_info "  2. Перейдите в директорию: cd $PROJECT_DIR"
log_info "  3. Отредактируйте .env.prod с реальными значениями"
log_info "  4. Запустите развертывание: ./deploy/deploy.sh"

log_warning "⚠️  Не забудьте настроить .env.prod перед запуском!"

# Опциональный запуск развертывания
read -p "Хотите запустить развертывание сейчас? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Запуск развертывания на сервере..."
    ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && ./deploy/deploy.sh"
else
    log_info "Развертывание пропущено. Запустите вручную когда будете готовы."
fi
