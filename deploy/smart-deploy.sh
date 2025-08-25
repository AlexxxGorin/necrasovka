#!/bin/bash

# Умный скрипт развертывания с автоматическим выбором свободного порта
# Использование: ./smart-deploy.sh [SERVER_IP] [SERVER_USER]

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

log_info "🚀 Умное развертывание Necrasovka Search на ${SERVER_USER}@${SERVER_IP}"

# Функция для поиска свободного порта на сервере
find_free_port() {
    local server_ip=$1
    local server_user=$2
    
    log_info "🔍 Поиск свободного порта на сервере..."
    
    # Список портов для проверки (в порядке предпочтения)
    local ports=(3000 3001 3002 8080 8081 8082 8000 8001 8002 9000 9001 9002)
    
    for port in "${ports[@]}"; do
        # Проверяем, свободен ли порт на сервере
        if ssh "$server_user@$server_ip" "! netstat -tln 2>/dev/null | grep -q ':$port '" 2>/dev/null; then
            echo $port
            return 0
        fi
    done
    
    # Если ни один из предпочтительных портов не свободен, ищем любой свободный
    local free_port=$(ssh "$server_user@$server_ip" "
        for port in {3000..9999}; do
            if ! netstat -tln 2>/dev/null | grep -q \":\$port \"; then
                echo \$port
                break
            fi
        done
    " 2>/dev/null)
    
    if [ -n "$free_port" ]; then
        echo $free_port
        return 0
    else
        return 1
    fi
}

# Находим свободный порт
FREE_PORT=$(find_free_port "$SERVER_IP" "$SERVER_USER")

if [ -z "$FREE_PORT" ]; then
    log_error "❌ Не удалось найти свободный порт на сервере"
    exit 1
fi

log_success "✅ Найден свободный порт: $FREE_PORT"

# Создаем временные файлы с правильным портом
log_info "📝 Создание конфигурации для порта $FREE_PORT..."

# Создаем временный docker-compose файл с правильным портом
cp docker-compose.smart.yml /tmp/docker-compose.smart.yml
sed -i "s/3000:80/$FREE_PORT:80/g" /tmp/docker-compose.smart.yml

# Синхронизируем проект с сервером
log_info "📦 Синхронизация проекта с сервером..."
./deploy/sync-to-server.sh "$SERVER_IP" "$SERVER_USER"

# Копируем временный docker-compose файл
scp /tmp/docker-compose.smart.yml "$SERVER_USER@$SERVER_IP:/opt/necrasovka/"

# Создаем скрипт развертывания на сервере
cat > /tmp/smart-server-deploy.sh << EOF
#!/bin/bash

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "\${BLUE}[INFO]\${NC} \$1"
}

log_success() {
    echo -e "\${GREEN}[SUCCESS]\${NC} \$1"
}

log_error() {
    echo -e "\${RED}[ERROR]\${NC} \$1"
}

cd /opt/necrasovka

# Проверяем .env.prod
if [[ ! -f .env.prod ]]; then
    log_info "Создание .env.prod из шаблона..."
    cp env.prod.template .env.prod
    log_info "⚠️ Не забудьте настроить .env.prod с реальными значениями!"
fi

# Останавливаем существующие контейнеры
log_info "Остановка существующих контейнеров..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
docker-compose -f docker-compose.simple.yml down 2>/dev/null || true
docker-compose -f docker-compose.smart.yml down 2>/dev/null || true

# Очистка старых образов
log_info "Очистка старых образов..."
docker system prune -af

# Сборка и запуск с умной конфигурацией
log_info "Сборка Docker образов..."
docker-compose -f docker-compose.smart.yml build --no-cache

log_info "Запуск сервисов на порту $FREE_PORT..."
docker-compose -f docker-compose.smart.yml up -d

# Ждем запуска
log_info "Ожидание запуска сервисов..."
sleep 30

# Проверяем статус
if docker-compose -f docker-compose.smart.yml ps | grep -q "Up"; then
    log_success "✅ Сервисы запущены успешно!"
else
    log_error "❌ Проблема с запуском сервисов"
    docker-compose -f docker-compose.smart.yml logs --tail=20
    exit 1
fi

# Проверяем доступность приложения
log_info "Проверка доступности приложения..."
sleep 10

if curl -f -s http://localhost:$FREE_PORT/health > /dev/null; then
    log_success "🎉 Развертывание завершено успешно!"
    log_info "🌐 Приложение доступно по адресу: http://\$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):$FREE_PORT"
    log_info "📚 API документация: http://\$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):$FREE_PORT/docs"
    log_info "🔍 Health check: http://\$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):$FREE_PORT/health"
    log_info "🧪 Автотесты: http://\$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP'):$FREE_PORT/test-search"
else
    log_error "❌ Приложение не отвечает. Проверьте логи:"
    docker-compose -f docker-compose.smart.yml logs --tail=20
fi

EOF

# Копируем и запускаем скрипт на сервере
scp /tmp/smart-server-deploy.sh "$SERVER_USER@$SERVER_IP:/tmp/"
ssh "$SERVER_USER@$SERVER_IP" "chmod +x /tmp/smart-server-deploy.sh && /tmp/smart-server-deploy.sh"

# Очистка временных файлов
rm -f /tmp/docker-compose.smart.yml /tmp/smart-server-deploy.sh

log_success "🎉 Умное развертывание завершено!"
log_info "🌐 Приложение развернуто на порту: $FREE_PORT"
log_info "🔗 Адрес: http://$SERVER_IP:$FREE_PORT"
