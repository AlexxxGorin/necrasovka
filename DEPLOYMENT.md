# 🚀 Руководство по развертыванию Necrasovka Search

Полное руководство по развертыванию поисковой системы Necrasovka на продакшн сервере.

## 📋 Требования к серверу

### Минимальные требования
- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 2GB (рекомендуется 4GB+)
- **CPU**: 2 ядра (рекомендуется 4+)
- **Диск**: 20GB свободного места (рекомендуется 50GB+)
- **Сеть**: Доступ в интернет, открытые порты 80, 22

### Рекомендуемые требования
- **RAM**: 8GB+
- **CPU**: 4+ ядра
- **Диск**: SSD 100GB+
- **Мониторинг**: Настроенный мониторинг ресурсов

## 🛠️ Быстрое развертывание

### Шаг 1: Подготовка проекта локально

```bash
# Клонирование репозитория
git clone <repository-url> necrasovka
cd necrasovka

# Проверка структуры проекта
ls -la
```

### Шаг 2: Синхронизация с сервером

```bash
# Синхронизация файлов на сервер
./deploy/sync-to-server.sh 89.169.3.47 root

# Или вручную через rsync
rsync -avz --exclude='.git' --exclude='venv' ./ root@89.169.3.47:/opt/necrasovka/
```

### Шаг 3: Подключение к серверу и настройка

```bash
# Подключение к серверу
ssh root@89.169.3.47

# Переход в рабочую директорию
cd /opt/necrasovka

# Настройка переменных окружения
cp env.prod.template .env.prod
nano .env.prod  # Отредактировать реальными значениями
```

### Шаг 4: Запуск развертывания

```bash
# Запуск автоматического развертывания
./deploy/deploy.sh
```

## ⚙️ Детальная настройка

### Конфигурация переменных окружения (.env.prod)

```bash
# OpenSearch конфигурация
OPENSEARCH_URL=rc1b-5el6fevs7qim0oss.mdb.yandexcloud.net
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your-password-here

# Typo API (опционально)
TYPO_API_URL=http://typo-fixer:8001/fix

# Настройки приложения
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### Структура Docker сервисов

```yaml
services:
  backend:    # FastAPI приложение на порту 8000
  frontend:   # Nginx + React на порту 80
```

### Настройка Nginx

Конфигурация Nginx автоматически настраивается для:
- Проксирования API запросов на бэкенд
- Кэширования статических ресурсов
- Gzip сжатия
- Безопасности headers

## 🔧 Управление сервисами

### Основные команды

```bash
# Статус сервисов
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Перезапуск сервисов
docker-compose -f docker-compose.prod.yml restart

# Остановка
docker-compose -f docker-compose.prod.yml down

# Полная пересборка
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Скрипты управления

```bash
# Мониторинг
./deploy/monitor.sh --all

# Обновление
./deploy/update.sh

# Настройка мониторинга
./deploy/setup-monitoring.sh
```

## 📊 Мониторинг и логирование

### Автоматический мониторинг

После запуска `./deploy/setup-monitoring.sh` настраивается:

- **Healthcheck каждые 5 минут** - проверка доступности сервисов
- **Сбор метрик каждые 10 минут** - CPU, память, диск, время отклика
- **Ротация логов** - автоматическая очистка старых логов
- **Автоматический перезапуск** при сбоях

### Команды мониторинга

```bash
# Быстрый статус
necrasovka-status

# Просмотр логов
necrasovka-logs

# Проверка здоровья
necrasovka-health

# Статистика
necrasovka-stats

# Перезапуск
necrasovka-restart
```

### Файлы логов

```
/var/log/necrasovka/healthcheck.log  # Проверки здоровья
/var/log/necrasovka/metrics.log      # Метрики системы
/opt/necrasovka/logs/                # Логи приложения
```

## 🔄 Обновление системы

### Автоматическое обновление

```bash
# На локальной машине - синхронизация изменений
./deploy/sync-to-server.sh

# На сервере - обновление
./deploy/update.sh
```

### Ручное обновление

```bash
# Остановка сервисов
docker-compose -f docker-compose.prod.yml down

# Получение новых файлов (git pull или rsync)
git pull origin main

# Пересборка и запуск
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## 🔒 Безопасность

### Настройка файрвола

```bash
# UFW (Ubuntu)
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw enable

# iptables (альтернатива)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
```

### SSL/HTTPS (рекомендуется)

Для продакшн использования рекомендуется настроить SSL:

```bash
# Установка Certbot
apt install certbot python3-certbot-nginx

# Получение сертификата
certbot --nginx -d your-domain.com

# Автообновление
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

## 🚨 Решение проблем

### Проблемы с запуском

```bash
# Проверка логов
docker-compose -f docker-compose.prod.yml logs

# Проверка портов
netstat -tlnp | grep :80
netstat -tlnp | grep :8000

# Проверка ресурсов
docker stats
df -h
free -h
```

### Проблемы с подключением к OpenSearch

```bash
# Проверка подключения
curl -k https://your-opensearch-host:9200/_cluster/health

# Проверка переменных окружения
docker-compose -f docker-compose.prod.yml exec backend env | grep OPENSEARCH
```

### Проблемы с производительностью

```bash
# Мониторинг ресурсов
htop
iotop
nethogs

# Оптимизация Docker
docker system prune -f
docker image prune -f
```

## 📈 Масштабирование

### Горизонтальное масштабирование

Для увеличения производительности можно:

1. **Увеличить количество workers бэкенда**:
   ```yaml
   # В docker-compose.prod.yml
   command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
   ```

2. **Добавить load balancer** (Nginx upstream)
3. **Использовать Redis для кэширования** результатов поиска

### Вертикальное масштабирование

```yaml
# Увеличение ресурсов контейнеров
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
```

## 🔧 Кастомизация

### Изменение портов

```yaml
# docker-compose.prod.yml
services:
  frontend:
    ports:
      - "8080:80"  # Изменить порт фронтенда
```

### Добавление дополнительных сервисов

```yaml
# Пример добавления Redis
services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    networks:
      - necrasovka-network
```

## 📞 Поддержка

### Контакты для поддержки
- **Разработчик**: [указать контакты]
- **Документация**: [ссылка на документацию]
- **Issues**: [ссылка на GitHub Issues]

### Полезные ссылки
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [OpenSearch Documentation](https://opensearch.org/docs/)

---

## ✅ Чеклист развертывания

- [ ] Сервер соответствует минимальным требованиям
- [ ] Проект синхронизирован на сервер
- [ ] Файл `.env.prod` настроен с реальными значениями
- [ ] Docker и Docker Compose установлены
- [ ] Сервисы запущены и работают
- [ ] Healthcheck проходит успешно
- [ ] Мониторинг настроен
- [ ] Файрвол настроен
- [ ] SSL сертификат установлен (для продакшн)
- [ ] Бэкапы настроены
- [ ] Команда знает процедуры обновления

**Успешное развертывание! 🎉**
