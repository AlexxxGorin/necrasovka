#!/bin/bash

# Скрипт для исправления и развертывания проекта
# Использование: ./fix-and-deploy.sh [SERVER_IP] [SERVER_USER]

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

log_info "🔧 Исправление и развертывание Necrasovka Search на ${SERVER_USER}@${SERVER_IP}"

# Проверка Docker локально (если доступен)
if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
    log_info "🧪 Тестирование сборки Docker образов локально..."
    
    # Тестируем сборку frontend
    log_info "Тестирование frontend образа..."
    if docker build -f Dockerfile.frontend -t necrasovka-frontend-test . > /tmp/frontend-build.log 2>&1; then
        log_success "✅ Frontend образ собирается успешно"
        docker rmi necrasovka-frontend-test 2>/dev/null || true
    else
        log_error "❌ Frontend образ не собирается:"
        tail -10 /tmp/frontend-build.log
        log_info "Продолжаем развертывание на сервере..."
    fi
    
    # Тестируем сборку backend
    log_info "Тестирование backend образа..."
    if docker build -f Dockerfile.backend -t necrasovka-backend-test . > /tmp/backend-build.log 2>&1; then
        log_success "✅ Backend образ собирается успешно"
        docker rmi necrasovka-backend-test 2>/dev/null || true
    else
        log_error "❌ Backend образ не собирается:"
        tail -10 /tmp/backend-build.log
        log_info "Продолжаем развертывание на сервере..."
    fi
    
    rm -f /tmp/frontend-build.log /tmp/backend-build.log
else
    log_warning "Docker недоступен локально, пропускаем локальное тестирование"
fi

# Синхронизация с сервером
log_info "📦 Синхронизация проекта с сервером..."
./deploy/sync-to-server.sh "$SERVER_IP" "$SERVER_USER"

# Развертывание на сервере
log_info "🚀 Запуск развертывания на сервере..."

# Создаем скрипт для выполнения на сервере
cat > /tmp/server-deploy.sh << 'EOF'
#!/bin/bash

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cd /opt/necrasovka

# Проверяем .env.prod
if [[ ! -f .env.prod ]]; then
    log_info "Создание .env.prod из шаблона..."
    cp env.prod.template .env.prod
    log_info "⚠️ Не забудьте настроить .env.prod с реальными значениями!"
fi

# Остановка существующих контейнеров
log_info "Остановка существующих контейнеров..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Очистка старых образов
log_info "Очистка старых образов..."
docker system prune -f

# Сборка с подробными логами
log_info "Сборка Docker образов..."
if docker-compose -f docker-compose.prod.yml build --no-cache --progress=plain; then
    log_success "✅ Образы собраны успешно"
else
    log_error "❌ Ошибка сборки образов"
    exit 1
fi

# Запуск сервисов
log_info "Запуск сервисов..."
if docker-compose -f docker-compose.prod.yml up -d; then
    log_success "✅ Сервисы запущены"
else
    log_error "❌ Ошибка запуска сервисов"
    exit 1
fi

# Ожидание запуска
log_info "Ожидание запуска сервисов..."
sleep 30

# Проверка статуса
log_info "📊 Статус контейнеров:"
docker-compose -f docker-compose.prod.yml ps

# Проверка health check
log_info "🔍 Проверка доступности приложения..."
for i in {1..10}; do
    if curl -s http://localhost/ > /dev/null 2>&1; then
        log_success "✅ Приложение доступно!"
        break
    else
        log_info "Попытка $i/10..."
        sleep 5
    fi
done

# Показываем логи если что-то не так
if ! curl -s http://localhost:3000/health > /dev/null 2>&1; then
    log_error "❌ Приложение недоступно, показываем логи:"
    docker-compose -f docker-compose.prod.yml logs --tail=20
fi

log_success "🎉 Развертывание завершено!"
log_info "🌐 Приложение доступно по адресу: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):3000"
log_info "📚 API документация: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):3000/docs"
log_info "🔍 Health check: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):3000/health"
log_info "🧪 Автотесты: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):3000/test-search"

EOF

# Копируем и запускаем скрипт на сервере
scp /tmp/server-deploy.sh "$SERVER_USER@$SERVER_IP:/tmp/"
ssh "$SERVER_USER@$SERVER_IP" "chmod +x /tmp/server-deploy.sh && /tmp/server-deploy.sh"

# Очистка
rm -f /tmp/server-deploy.sh

log_success "🎉 Развертывание завершено успешно!"
log_info "📋 Полезные команды для управления:"
log_info "  Статус:     ssh $SERVER_USER@$SERVER_IP 'cd /opt/necrasovka && docker-compose -f docker-compose.prod.yml ps'"
log_info "  Логи:       ssh $SERVER_USER@$SERVER_IP 'cd /opt/necrasovka && docker-compose -f docker-compose.prod.yml logs -f'"
log_info "  Рестарт:    ssh $SERVER_USER@$SERVER_IP 'cd /opt/necrasovka && docker-compose -f docker-compose.prod.yml restart'"
log_info "  Остановка:  ssh $SERVER_USER@$SERVER_IP 'cd /opt/necrasovka && docker-compose -f docker-compose.prod.yml down'"
