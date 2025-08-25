#!/bin/bash

# Скрипт быстрого обновления Necrasovka Search
# Использование: ./update.sh

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

PROJECT_DIR="/opt/necrasovka"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   log_error "Этот скрипт должен запускаться с правами root"
   exit 1
fi

log_info "🔄 Начинаем обновление Necrasovka Search..."

cd $PROJECT_DIR

# Проверка текущего состояния
log_info "Проверка текущего состояния сервисов..."
docker-compose -f $DOCKER_COMPOSE_FILE ps

# Создание бэкапа
log_info "Создание бэкапа..."
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /opt/backups/necrasovka/$BACKUP_TIMESTAMP

# Бэкап логов и конфигурации
cp -r logs /opt/backups/necrasovka/$BACKUP_TIMESTAMP/ 2>/dev/null || true
cp .env.prod /opt/backups/necrasovka/$BACKUP_TIMESTAMP/ 2>/dev/null || true

log_success "Бэкап создан: /opt/backups/necrasovka/$BACKUP_TIMESTAMP"

# Остановка сервисов
log_info "Остановка сервисов..."
docker-compose -f $DOCKER_COMPOSE_FILE down

# Сборка новых образов
log_info "Сборка новых образов..."
docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache

# Очистка старых образов
log_info "Очистка старых образов..."
docker image prune -f

# Запуск обновленных сервисов
log_info "Запуск обновленных сервисов..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

# Ожидание запуска
log_info "Ожидание запуска сервисов..."
sleep 30

# Проверка здоровья
log_info "Проверка состояния сервисов..."
if docker-compose -f $DOCKER_COMPOSE_FILE ps | grep -q "Up (healthy)"; then
    log_success "✅ Обновление завершено успешно!"
else
    log_warning "⚠️  Некоторые сервисы могут быть не готовы. Проверьте логи:"
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=20
fi

# Финальная проверка
if curl -f -s http://localhost/health > /dev/null; then
    log_success "🎉 Приложение работает корректно!"
    log_info "Приложение доступно по адресу: http://$(hostname -I | awk '{print $1}')"
else
    log_error "❌ Приложение не отвечает. Откат к бэкапу..."
    
    # Откат
    docker-compose -f $DOCKER_COMPOSE_FILE down
    cp /opt/backups/necrasovka/$BACKUP_TIMESTAMP/.env.prod . 2>/dev/null || true
    docker-compose -f $DOCKER_COMPOSE_FILE up -d
    
    log_error "Произведен откат. Проверьте логи ошибок."
    exit 1
fi

log_info "Обновление завершено. Бэкап сохранен в /opt/backups/necrasovka/$BACKUP_TIMESTAMP"
