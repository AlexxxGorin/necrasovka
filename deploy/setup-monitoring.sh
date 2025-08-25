#!/bin/bash

# Скрипт настройки мониторинга для Necrasovka Search
# Использование: ./setup-monitoring.sh

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

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   log_error "Этот скрипт должен запускаться с правами root"
   exit 1
fi

log_info "🔧 Настройка мониторинга Necrasovka Search..."

# Установка необходимых пакетов
log_info "Установка необходимых пакетов..."
apt-get update
apt-get install -y htop iotop nethogs jq curl wget logrotate

# Настройка cron для регулярных проверок
log_info "Настройка cron заданий..."

# Создание скрипта проверки здоровья
cat > /usr/local/bin/necrasovka-healthcheck << 'EOF'
#!/bin/bash
# Скрипт проверки здоровья Necrasovka Search

LOG_FILE="/var/log/necrasovka/healthcheck.log"
PROJECT_DIR="/opt/necrasovka"

# Создание директории логов
mkdir -p /var/log/necrasovka

# Функция логирования
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_FILE
}

cd $PROJECT_DIR

# Проверка Docker сервисов
if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    log_message "ERROR: Docker services are down. Attempting restart..."
    docker-compose -f docker-compose.prod.yml up -d
    sleep 30
fi

# Проверка HTTP доступности
if ! curl -f -s http://localhost/health > /dev/null; then
    log_message "ERROR: HTTP health check failed"
    # Отправка уведомления (можно настроить email или Telegram)
    # echo "Necrasovka Search is down!" | mail -s "Service Alert" admin@example.com
else
    log_message "INFO: Health check passed"
fi

# Проверка использования диска
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    log_message "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# Очистка старых логов (старше 7 дней)
find /var/log/necrasovka -name "*.log" -mtime +7 -delete 2>/dev/null || true
EOF

chmod +x /usr/local/bin/necrasovka-healthcheck

# Добавление cron задания
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/necrasovka-healthcheck") | crontab -

log_success "Healthcheck настроен (каждые 5 минут)"

# Настройка logrotate для логов приложения
log_info "Настройка ротации логов..."
cat > /etc/logrotate.d/necrasovka << 'EOF'
/var/log/necrasovka/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    copytruncate
}

/opt/necrasovka/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 1000 1000
    postrotate
        /usr/local/bin/docker-compose -f /opt/necrasovka/docker-compose.prod.yml restart backend 2>/dev/null || true
    endscript
}
EOF

# Создание скрипта для сбора метрик
log_info "Создание скрипта сбора метрик..."
cat > /usr/local/bin/necrasovka-metrics << 'EOF'
#!/bin/bash
# Скрипт сбора метрик Necrasovka Search

METRICS_FILE="/var/log/necrasovka/metrics.log"
PROJECT_DIR="/opt/necrasovka"

# Создание директории логов
mkdir -p /var/log/necrasovka

cd $PROJECT_DIR

# Получение метрик
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Системные метрики
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

# Docker метрики
BACKEND_STATUS=$(docker inspect necrasovka-backend --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
FRONTEND_STATUS=$(docker inspect necrasovka-frontend --format='{{.State.Status}}' 2>/dev/null || echo "unknown")

# HTTP метрики
HTTP_RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost/health 2>/dev/null || echo "0")

# Запись метрик в JSON формате
echo "{
    \"timestamp\": \"$TIMESTAMP\",
    \"system\": {
        \"cpu_usage\": \"$CPU_USAGE\",
        \"memory_usage\": \"$MEMORY_USAGE\",
        \"disk_usage\": \"$DISK_USAGE\"
    },
    \"containers\": {
        \"backend_status\": \"$BACKEND_STATUS\",
        \"frontend_status\": \"$FRONTEND_STATUS\"
    },
    \"performance\": {
        \"http_response_time\": \"$HTTP_RESPONSE_TIME\"
    }
}" >> $METRICS_FILE
EOF

chmod +x /usr/local/bin/necrasovka-metrics

# Добавление cron задания для метрик
(crontab -l 2>/dev/null; echo "*/10 * * * * /usr/local/bin/necrasovka-metrics") | crontab -

log_success "Сбор метрик настроен (каждые 10 минут)"

# Создание скрипта для просмотра метрик
log_info "Создание скрипта просмотра метрик..."
cat > /usr/local/bin/necrasovka-stats << 'EOF'
#!/bin/bash
# Скрипт просмотра статистики Necrasovka Search

METRICS_FILE="/var/log/necrasovka/metrics.log"
HEALTHCHECK_FILE="/var/log/necrasovka/healthcheck.log"

echo "=== NECRASOVKA SEARCH STATISTICS ==="
echo "Время: $(date)"
echo

if [ -f "$METRICS_FILE" ]; then
    echo "=== ПОСЛЕДНИЕ МЕТРИКИ ==="
    tail -1 "$METRICS_FILE" | jq '.' 2>/dev/null || echo "Ошибка парсинга метрик"
    echo
    
    echo "=== СРЕДНИЕ ЗНАЧЕНИЯ ЗА ПОСЛЕДНИЙ ЧАС ==="
    tail -6 "$METRICS_FILE" | jq -r '.system.cpu_usage' | awk '{sum+=$1; count++} END {if(count>0) printf "CPU: %.1f%%\n", sum/count}'
    tail -6 "$METRICS_FILE" | jq -r '.system.memory_usage' | awk '{sum+=$1; count++} END {if(count>0) printf "Memory: %.1f%%\n", sum/count}'
    tail -6 "$METRICS_FILE" | jq -r '.performance.http_response_time' | awk '{sum+=$1; count++} END {if(count>0) printf "Response Time: %.3fs\n", sum/count}'
fi

if [ -f "$HEALTHCHECK_FILE" ]; then
    echo
    echo "=== ПОСЛЕДНИЕ ПРОВЕРКИ ЗДОРОВЬЯ ==="
    tail -5 "$HEALTHCHECK_FILE"
fi

echo
echo "=== СТАТУС DOCKER КОНТЕЙНЕРОВ ==="
cd /opt/necrasovka
docker-compose -f docker-compose.prod.yml ps
EOF

chmod +x /usr/local/bin/necrasovka-stats

# Настройка файрвола
if command -v ufw &> /dev/null; then
    log_info "Настройка файрвола..."
    ufw allow 80/tcp comment "Necrasovka HTTP"
    ufw allow 22/tcp comment "SSH"
    log_success "Файрвол настроен"
fi

# Создание алиасов для удобства
log_info "Создание алиасов..."
cat >> /root/.bashrc << 'EOF'

# Necrasovka Search aliases
alias necrasovka-status='cd /opt/necrasovka && ./deploy/monitor.sh --status'
alias necrasovka-logs='cd /opt/necrasovka && ./deploy/monitor.sh --logs'
alias necrasovka-health='cd /opt/necrasovka && ./deploy/monitor.sh --health'
alias necrasovka-restart='cd /opt/necrasovka && docker-compose -f docker-compose.prod.yml restart'
alias necrasovka-update='cd /opt/necrasovka && ./deploy/update.sh'
alias necrasovka-stats='/usr/local/bin/necrasovka-stats'
EOF

log_success "✅ Мониторинг настроен!"

log_info "Доступные команды:"
log_info "  necrasovka-status  - Статус сервисов"
log_info "  necrasovka-logs    - Просмотр логов"
log_info "  necrasovka-health  - Проверка здоровья"
log_info "  necrasovka-restart - Перезапуск сервисов"
log_info "  necrasovka-update  - Обновление приложения"
log_info "  necrasovka-stats   - Просмотр статистики"

log_info "Файлы логов:"
log_info "  /var/log/necrasovka/healthcheck.log - Проверки здоровья"
log_info "  /var/log/necrasovka/metrics.log     - Метрики системы"
log_info "  /opt/necrasovka/logs/               - Логи приложения"

log_warning "⚠️  Для применения алиасов выполните: source /root/.bashrc"
