#!/usr/bin/env python3
"""
Скрипт для запуска автотестов системы поиска
Использование: python run_tests.py
"""

import asyncio
import sys
import os

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.search_tests import run_search_tests

async def main():
    """Главная функция"""
    try:
        print("🧪 Запуск автотестов системы поиска...")
        summary = await run_search_tests()
        
        # Возвращаем код выхода на основе результатов
        if summary['pass_rate'] >= 70:
            print("\n✅ Тесты прошли успешно!")
            return 0
        else:
            print("\n❌ Некоторые тесты провалились!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Критическая ошибка при выполнении тестов: {e}")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
