#!/usr/bin/env python3
"""
Проверяет SQL-запросы для Looker Studio и выводит инструкцию.

Запуск:
    python setup_looker.py          # проверить все SQL
    python setup_looker.py --copy funnel_daily   # скопировать SQL в буфер обмена
"""

import subprocess
import sys
import os
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

BQ_PROJECT = "claude-code-486108"
SERVICE_ACCOUNT_FILE = "service_account.json"

SCOPES = ["https://www.googleapis.com/auth/bigquery"]

SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "looker_sql")

SQL_FILES = {
    "funnel_daily": "Воронка по дням (фильтры: дата, источник, страна, этап)",
    "sessions_daily": "Поведение сессий (фильтры: дата, источник, страна)",
    "transactions": "Транзакции (каждая покупка с атрибуцией)",
}


def validate_sql():
    """Проверяет все SQL-запросы на выполнимость."""
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = bigquery.Client(credentials=credentials, project=BQ_PROJECT)

    print("Проверка SQL-запросов для Looker Studio")
    print("=" * 50)

    all_ok = True
    for name, desc in SQL_FILES.items():
        path = os.path.join(SQL_DIR, f"{name}.sql")
        with open(path) as f:
            sql = f.read()

        try:
            rows = list(client.query(sql).result())
            print(f"  ✓ {name}.sql — {len(rows)} строк ({desc})")
        except Exception as e:
            print(f"  ✗ {name}.sql — ОШИБКА: {e}")
            all_ok = False

    print("=" * 50)
    return all_ok


def print_instructions():
    print()
    print("ИНСТРУКЦИЯ: Настройка Looker Studio")
    print("=" * 50)
    print()
    print("1. Открой https://lookerstudio.google.com")
    print("2. Нажми '+ Create' → 'Report'")
    print("3. Для каждого SQL-файла добавь источник данных:")
    print()

    for name, desc in SQL_FILES.items():
        path = os.path.join(SQL_DIR, f"{name}.sql")
        print(f"   [{name}] {desc}")
        print(f"   → Add data → BigQuery → Custom Query → Project: {BQ_PROJECT}")
        print(f"   → Вставь содержимое файла: {path}")
        print()

    print("4. Рекомендуемые графики:")
    print("   - Bar chart (воронка): stage по оси X, users по оси Y, фильтр traffic_source")
    print("   - Time series: date по оси X, users по оси Y, разбивка по stage")
    print("   - Scorecard: sessions, median_eng_sec, avg_pages")
    print("   - Table: transactions с деталями")
    print()
    print("5. Добавь фильтры (Filter control):")
    print("   - Date range picker (по полю date)")
    print("   - Drop-down: traffic_source")
    print("   - Drop-down: country")
    print()
    print("Подробнее: looker_instructions.md")


def copy_sql(name):
    """Копирует SQL в буфер обмена (macOS)."""
    path = os.path.join(SQL_DIR, f"{name}.sql")
    if not os.path.exists(path):
        print(f"Файл не найден: {path}")
        print(f"Доступные: {', '.join(SQL_FILES.keys())}")
        return

    with open(path) as f:
        sql = f.read()
    subprocess.run(["pbcopy"], input=sql.encode(), check=True)
    print(f"✓ {name}.sql скопирован в буфер обмена")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--copy" in args:
        idx = args.index("--copy")
        if idx + 1 < len(args):
            copy_sql(args[idx + 1])
        else:
            print("Использование: python setup_looker.py --copy <name>")
            print(f"Доступные: {', '.join(SQL_FILES.keys())}")
    else:
        ok = validate_sql()
        print_instructions()
        if not ok:
            sys.exit(1)
