#!/bin/bash

# Скрипт развертывания Necrasovka Search на сервере
# Использование: ./deploy.sh [--update]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
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

# Конфигурация
PROJECT_NAME="necrasovka"
PROJECT_DIR="/opt/necrasovka"
BACKUP_DIR="/opt/backups/necrasovka"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
SIMPLE_COMPOSE_FILE="docker-compose.simple.yml"

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   log_error "Этот скрипт должен запускаться с правами root"
   exit 1
fi

log_info "🚀 Начинаем развертывание Necrasovka Search..."

# Создание директорий
log_info "Создание рабочих директорий..."
mkdir -p $PROJECT_DIR
mkdir -p $BACKUP_DIR
mkdir -p /var/log/necrasovka

# Установка Docker и Docker Compose (если не установлены)
if ! command -v docker &> /dev/null; then
    log_info "Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl enable docker
    systemctl start docker
    rm get-docker.sh
    log_success "Docker установлен"
else
    log_info "Docker уже установлен"
fi

# Проверка что Docker запущен
if ! docker info &> /dev/null; then
    log_info "Запуск Docker..."
    systemctl start docker
    sleep 5
    if ! docker info &> /dev/null; then
        log_error "Не удается запустить Docker"
        exit 1
    fi
fi

if ! command -v docker-compose &> /dev/null; then
    log_info "Установка Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose установлен"
fi

# Переход в рабочую директорию
cd $PROJECT_DIR

# Бэкап существующих данных (если это обновление)
if [[ "$1" == "--update" ]] && [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
    log_info "Создание бэкапа..."
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p $BACKUP_DIR/$BACKUP_TIMESTAMP
    
    # Остановка сервисов
    docker-compose -f $DOCKER_COMPOSE_FILE down
    
    # Бэкап конфигураций
    cp -r . $BACKUP_DIR/$BACKUP_TIMESTAMP/
    log_success "Бэкап создан: $BACKUP_DIR/$BACKUP_TIMESTAMP"
fi

log_info "Копирование файлов проекта..."
# Здесь предполагается, что файлы уже скопированы на сервер

# Проверка наличия .env.prod
if [[ ! -f ".env.prod" ]]; then
    log_warning "Файл .env.prod не найден. Создание из шаблона..."
    if [[ -f "env.prod.template" ]]; then
        cp env.prod.template .env.prod
        log_warning "⚠️  ВНИМАНИЕ: Необходимо отредактировать .env.prod с реальными значениями!"
    else
        log_error "Шаблон env.prod.template не найден!"
        exit 1
    fi
fi

# Создание логов директории
mkdir -p logs
chown -R 1000:1000 logs

# Сборка и запуск контейнеров
log_info "Сборка Docker образов..."
if ! docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache; then
    log_error "Ошибка сборки Docker образов"
    log_info "Проверьте логи выше для деталей"
    exit 1
fi

log_info "Запуск сервисов..."
if ! docker-compose -f $DOCKER_COMPOSE_FILE up -d; then
    log_error "Ошибка запуска сервисов"
    
    # Проверяем, не связана ли ошибка с занятым портом
    if docker-compose -f $DOCKER_COMPOSE_FILE logs 2>&1 | grep -q "address already in use\|bind.*failed"; then
        log_warning "Обнаружен конфликт портов. Переключаемся на упрощенную конфигурацию (порт 8080)..."
        
        # Останавливаем текущие контейнеры
        docker-compose -f $DOCKER_COMPOSE_FILE down 2>/dev/null || true
        
        # Запускаем с упрощенной конфигурацией
        if docker-compose -f $SIMPLE_COMPOSE_FILE up -d; then
            log_success "Сервисы запущены с упрощенной конфигурацией"
            DOCKER_COMPOSE_FILE=$SIMPLE_COMPOSE_FILE
        else
            log_error "Не удалось запустить даже с упрощенной конфигурацией"
            exit 1
        fi
    else
        log_info "Проверьте конфигурацию и логи"
        exit 1
    fi
fi

# Ожидание запуска сервисов
log_info "Ожидание запуска сервисов..."
sleep 30

# Проверка здоровья сервисов
log_info "Проверка состояния сервисов..."
if docker-compose -f $DOCKER_COMPOSE_FILE ps | grep -q "Up (healthy)"; then
    log_success "✅ Сервисы успешно запущены!"
else
    log_warning "⚠️  Некоторые сервисы могут быть не готовы. Проверьте логи:"
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=50
fi

# Настройка автозапуска
log_info "Настройка автозапуска..."
cat > /etc/systemd/system/necrasovka.service << EOF
[Unit]
Description=Necrasovka Search Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/local/bin/docker-compose -f $DOCKER_COMPOSE_FILE up -d
ExecStop=/usr/local/bin/docker-compose -f $DOCKER_COMPOSE_FILE down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable necrasovka.service
log_success "Автозапуск настроен"

# Настройка logrotate
log_info "Настройка ротации логов..."
cat > /etc/logrotate.d/necrasovka << EOF
/var/log/necrasovka/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE restart backend 2>/dev/null || true
    endscript
}
EOF

# Определяем порт из конфигурации
if [[ "$DOCKER_COMPOSE_FILE" == "$SIMPLE_COMPOSE_FILE" ]]; then
    APP_PORT="3000"
else
    APP_PORT="3000"  # Теперь используем 3000 в обеих конфигурациях
fi

# Настройка файрвола (если установлен ufw)
if command -v ufw &> /dev/null; then
    log_info "Настройка файрвола..."
    ufw allow $APP_PORT/tcp
    ufw allow 22/tcp
    log_success "Файрвол настроен"
fi

# Финальная проверка
log_info "Финальная проверка..."
sleep 10

if curl -f -s http://localhost:$APP_PORT/health > /dev/null; then
    log_success "🎉 Развертывание завершено успешно!"
    log_info "🌐 Приложение доступно по адресу: http://$(hostname -I | awk '{print $1}'):$APP_PORT"
    log_info "📚 API документация: http://$(hostname -I | awk '{print $1}'):$APP_PORT/docs"
    log_info "🔍 Health check: http://$(hostname -I | awk '{print $1}'):$APP_PORT/health"
    log_info "🧪 Автотесты: http://$(hostname -I | awk '{print $1}'):$APP_PORT/test-search"
    log_info "Для просмотра логов: docker-compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE logs -f"
else
    log_error "❌ Приложение не отвечает. Проверьте логи:"
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=20
    exit 1
fi

log_info "Полезные команды:"
log_info "  Просмотр статуса: docker-compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE ps"
log_info "  Просмотр логов: docker-compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE logs -f"
log_info "  Перезапуск: docker-compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE restart"
log_info "  Остановка: docker-compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE down"
