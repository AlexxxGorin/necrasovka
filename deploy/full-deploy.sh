#!/bin/bash

# Полный скрипт развертывания Necrasovka Search
# Выполняет все этапы от синхронизации до мониторинга
# Использование: ./full-deploy.sh [SERVER_IP] [SERVER_USER]

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

# Параметры
SERVER_IP=${1:-"89.169.3.47"}
SERVER_USER=${2:-"root"}
PROJECT_DIR="/opt/necrasovka"

log_info "🚀 Полное развертывание Necrasovka Search на $SERVER_USER@$SERVER_IP"

# Этап 1: Синхронизация проекта
log_info "📦 Этап 1: Синхронизация проекта с сервером..."
./deploy/sync-to-server.sh $SERVER_IP $SERVER_USER

# Этап 2: Развертывание на сервере
log_info "🔧 Этап 2: Развертывание на сервере..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && ./deploy/deploy.sh"

# Этап 3: Настройка мониторинга
log_info "📊 Этап 3: Настройка мониторинга..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && ./deploy/setup-monitoring.sh"

# Этап 4: Финальная проверка
log_info "✅ Этап 4: Финальная проверка..."
sleep 10

# Проверка доступности
if curl -f -s http://$SERVER_IP/health > /dev/null; then
    log_success "🎉 Развертывание завершено успешно!"
    log_info "Приложение доступно по адресу: http://$SERVER_IP"
else
    log_error "❌ Приложение не отвечает. Проверьте логи на сервере."
    exit 1
fi

# Показать статистику
log_info "📈 Статус сервисов:"
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && ./deploy/monitor.sh --status"

log_success "✅ Полное развертывание завершено!"

log_info "🔗 Полезные команды для управления на сервере:"
log_info "  ssh $SERVER_USER@$SERVER_IP"
log_info "  cd $PROJECT_DIR"
log_info "  ./deploy/monitor.sh --all     # Полный мониторинг"
log_info "  ./deploy/update.sh           # Обновление"
log_info "  necrasovka-status            # Быстрый статус"

log_warning "⚠️  Не забудьте:"
log_warning "  1. Настроить SSL сертификат для продакшн"
log_warning "  2. Настроить регулярные бэкапы"
log_warning "  3. Проверить настройки безопасности"
