# МебельОрг — демонстрационный экзамен 2026

Веб-приложение на Django 5.2, `uv` и PostgreSQL 16.

Реализованы каталог товаров, поиск, фильтрация и сортировка, авторизация по
ролям, CRUD товаров и заказов, обработка изображений и автоматический импорт
исходных данных.

## Что должно быть установлено

- Windows 10 или 11;
- PostgreSQL 16 с запущенной службой;
- `uv`;
- доступ к интернету при первом запуске для установки Python-зависимостей.

## Быстрый запуск

Откройте PowerShell в корне проекта. Один раз выполните установку:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
Unblock-File .\setup.ps1
.\setup.ps1
```

Скрипт рассчитан на экзаменационные настройки PostgreSQL:

- пользователь `postgres`;
- пароль `postgres`;
- сервер `localhost`;
- порт `5432`;
- база `furniture_demo`.

Если пароль пользователя `postgres` отличается от `postgres`, установщик
попросит ввести действующий пароль. Введенные символы в PowerShell не
отображаются.

Установочный скрипт автоматически:

1. Найдет PostgreSQL 16.
2. Подключится к `localhost:5432`.
3. Создаст базу `furniture_demo`, если ее еще нет.
4. Запишет локальные настройки подключения в `.env`.
5. Установит зависимости через `uv`.
6. Применит миграции.
7. Импортирует данные из CSV и подготовит изображения.

После успешной установки `setup.ps1` можно удалить.

Запуск проекта:

```powershell
uv run python src/manage.py runserver
```

Откройте <http://127.0.0.1:8000>. Остановка сервера: `Ctrl+C`.

Повторный запуск выполняется той же командой:

```powershell
uv run python src/manage.py runserver
```

## Структура

```text
mebelorg_demo/
├── src/                    # Весь код Django
│   ├── manage.py
│   ├── config/             # Настройки и маршруты проекта
│   ├── furniture/          # Модели, формы, views, тесты и миграции
│   ├── templates/          # HTML-шаблоны
│   └── static/             # CSS, JavaScript, логотип и иконка
├── data/
│   ├── normalized_3nf.xlsx # Нормализованная база в 3НФ
│   └── csv/                # Таблицы для автоматического импорта
├── database/schema.sql     # SQL-схема PostgreSQL
├── docs/                   # ER-диаграмма, алгоритм и отчет
├── exam_materials/         # Исходные материалы задания
├── seed_media/             # Исходные изображения товаров
├── pyproject.toml          # Python-зависимости
├── uv.lock                 # Зафиксированные версии зависимостей
└── setup.ps1               # Одноразовая подготовка проекта
```

Папки `.venv`, `media` и файл `.env` создаются локально и в архив не входят.

## Учетные записи

| Роль | Логин | Пароль |
|---|---|---|
| Администратор | `94d5ous@gmail.com` | `uzWC67` |
| Менеджер | `ptec8ym@yahoo.com` | `LdNyos` |
| Клиент | `yzls62@outlook.com` | `JlFRCZ` |

Полный список находится в `data/csv/users.csv`. В PostgreSQL пароли хранятся
только в виде хешей Django.

## Артефакты задания

- `data/normalized_3nf.xlsx` — нормализованные таблицы и связи.
- `data/csv/` — CSV-файлы для импорта.
- `database/schema.sql` — схема предметной области.
- `docs/er_diagram.pdf` — ER-диаграмма.
- `docs/application_algorithm.pdf` — блок-схема алгоритма.
- `docs/test_report.docx` — отчет о тестировании.

В исходных данных невозможная дата `30.02.2024` исправлена на `29.02.2024`.
Заказ №2 содержит дату заказа позже даты выдачи; исходное значение сохранено,
а проблема отмечена в `data/csv/data_issues.csv`.

## Проверка

Проверка после установки:

```powershell
uv run python src/manage.py test furniture
uv run python src/manage.py check
uv run python src/manage.py findstatic css/app.css
```
