# 🚀 Быстрый старт Necrasovka Search

## Локальная разработка

```bash
# 1. Установка зависимостей
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd frontend/frontend-necrasovka
npm install
cd ../..

# 2. Настройка окружения
# Создать .env файл с реальными значениями OpenSearch

# 3. Запуск
# Терминал 1 - Backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Терминал 2 - Frontend
cd frontend/frontend-necrasovka
npm run dev
```

Приложение доступно на http://localhost:5173

## Продакшн развертывание

### ⭐ Вариант 1: Умное развертывание (РЕКОМЕНДУЕТСЯ)

```bash
# Проверка готовности
./deploy/check-deployment.sh

# Умное развертывание с автопоиском свободного порта
./deploy/smart-deploy.sh 89.169.3.47 root
```

### Вариант 2: Автоматическое развертывание

```bash
# Полное развертывание одной командой
./deploy/full-deploy.sh 89.169.3.47 root
```

### Вариант 3: Пошаговое развертывание

```bash
# 1. Синхронизация с сервером
./deploy/sync-to-server.sh 89.169.3.47 root

# 2. Подключение к серверу
ssh root@89.169.3.47

# 3. Настройка переменных окружения
cd /opt/necrasovka
cp env.prod.template .env.prod
nano .env.prod  # Заполнить реальными значениями

# 4. Развертывание
./deploy/deploy.sh

# 5. Настройка мониторинга
./deploy/setup-monitoring.sh
```

## Управление на сервере

```bash
# Статус
necrasovka-status

# Логи
necrasovka-logs

# Перезапуск
necrasovka-restart

# Обновление
necrasovka-update

# Полный мониторинг
./deploy/monitor.sh --all
```

## Основные URL

- **Приложение**: http://89.169.3.47:3000 (порт автоматически определяется)
- **API документация**: http://89.169.3.47:3000/docs
- **Health check**: http://89.169.3.47:3000/health
- **Автотесты**: http://89.169.3.47:3000/test-search

## Структура проекта

```
necrasovka/
├── app/                    # Backend (FastAPI)
├── frontend/              # Frontend (React + Vite)
├── deploy/                # Скрипты развертывания
├── docker-compose.prod.yml # Продакшн конфигурация
├── docker-compose.simple.yml # Упрощенная конфигурация
├── Dockerfile.backend     # Backend Docker образ
├── Dockerfile.frontend    # Frontend Docker образ
├── DEPLOYMENT.md          # Полная документация
├── DEPLOYMENT_FIXES.md    # Исправления проблем
└── DEPLOYMENT_SUMMARY.md  # Сводка развертывания
```

## Переменные окружения (.env.prod)

```bash
OPENSEARCH_URL=your-opensearch-host
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your-password
TYPO_API_URL=http://typo-fixer:8001/fix
ENVIRONMENT=production
DEBUG=false
```

## 🧹 Очистка проекта

Удалены устаревшие файлы после оптимизации:
- ~~`Dockerfile`~~ → `Dockerfile.backend`
- ~~`docker-compose.yml`~~ → `docker-compose.prod.yml`
- ~~`test_search_modes.py`~~ (временный файл)
- ~~`deploy/check-ports.sh`~~ → включено в `smart-deploy.sh`
- ~~`frontend/.../vite.config.prod.js`~~ → используется основной `vite.config.js`

## Поддержка

- **Полная документация**: `DEPLOYMENT.md`
- **Сводка развертывания**: `DEPLOYMENT_SUMMARY.md`
- **Исправления проблем**: `DEPLOYMENT_FIXES.md`
- **Мониторинг**: `./deploy/monitor.sh --help`
- **Логи**: `/var/log/necrasovka/`
