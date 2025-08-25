#!/bin/bash

# Скрипт мониторинга Necrasovka Search
# Использование: ./monitor.sh [--status|--logs|--health|--resources]

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

# Переход в рабочую директорию
cd $PROJECT_DIR

show_status() {
    log_info "📊 Статус сервисов:"
    docker-compose -f $DOCKER_COMPOSE_FILE ps
    echo
    
    log_info "🔍 Детали контейнеров:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

show_logs() {
    log_info "📝 Логи сервисов (последние 50 строк):"
    echo "=== BACKEND LOGS ==="
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=50 backend
    echo
    echo "=== FRONTEND LOGS ==="
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=50 frontend
}

check_health() {
    log_info "🏥 Проверка здоровья сервисов:"
    
    # Проверка backend
    if curl -f -s http://localhost/health > /dev/null; then
        log_success "✅ Backend: Healthy"
    else
        log_error "❌ Backend: Unhealthy"
    fi
    
    # Проверка frontend
    if curl -f -s http://localhost/ > /dev/null; then
        log_success "✅ Frontend: Healthy"
    else
        log_error "❌ Frontend: Unhealthy"
    fi
    
    # Проверка Docker контейнеров
    backend_status=$(docker inspect necrasovka-backend --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    frontend_status=$(docker inspect necrasovka-frontend --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    
    echo
    log_info "Docker Health Status:"
    echo "  Backend: $backend_status"
    echo "  Frontend: $frontend_status"
}

show_resources() {
    log_info "💾 Использование ресурсов:"
    
    echo "=== SYSTEM RESOURCES ==="
    echo "CPU Usage:"
    top -bn1 | grep "Cpu(s)" | awk '{print $2 $3 $4 $5}'
    
    echo
    echo "Memory Usage:"
    free -h
    
    echo
    echo "Disk Usage:"
    df -h /
    
    echo
    echo "=== DOCKER RESOURCES ==="
    docker system df
    
    echo
    echo "=== CONTAINER RESOURCES ==="
    docker stats --no-stream
}

run_search_test() {
    log_info "🧪 Запуск тестов поиска:"
    
    # Простой тест API
    if curl -s "http://localhost/search?index=my-books-index&q=test&search_mode=both" | jq -r '.total.value' > /dev/null 2>&1; then
        log_success "✅ Search API: Working"
    else
        log_error "❌ Search API: Failed"
    fi
    
    # Тест автотестов (если доступен)
    if curl -s "http://localhost/test-search" > /dev/null 2>&1; then
        log_success "✅ Test Suite: Available"
    else
        log_warning "⚠️  Test Suite: Not available"
    fi
}

show_help() {
    echo "Necrasovka Search Monitoring Script"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  --status      Show service status and container stats"
    echo "  --logs        Show recent logs from all services"
    echo "  --health      Check health of all services"
    echo "  --resources   Show system and Docker resource usage"
    echo "  --test        Run basic functionality tests"
    echo "  --all         Show all monitoring information"
    echo "  --help        Show this help message"
    echo
    echo "If no option is provided, shows basic status information."
}

# Основная логика
case "${1:-}" in
    --status)
        show_status
        ;;
    --logs)
        show_logs
        ;;
    --health)
        check_health
        ;;
    --resources)
        show_resources
        ;;
    --test)
        run_search_test
        ;;
    --all)
        show_status
        echo
        check_health
        echo
        show_resources
        echo
        run_search_test
        ;;
    --help)
        show_help
        ;;
    *)
        log_info "🔍 Necrasovka Search - Быстрый статус"
        echo "Время: $(date)"
        echo
        show_status
        echo
        check_health
        echo
        log_info "Для подробной информации используйте: $0 --help"
        ;;
esac
