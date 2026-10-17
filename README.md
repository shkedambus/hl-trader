# hl-trader

Показывает, за какими трейдерами HyperLiquid стоит следить, почему именно за ними и сколько данных стоит за этим выводом.

Документы: [одностраничник](docs/OnePager.md), [PRD](docs/PRD.md), [SRS](docs/SRS.md), [User Stories](docs/UserStories.md), [RTM](docs/RTM.md), [план](docs/plan.md), [ERD](docs/erd.md), [исследование](docs/research.md).

## Как устроен отбор

1. Публичный рейтинг биржи (бесплатно, без веса API) -> предварительный отсев (FR-1).
2. Для кандидатов по порядку приоритета: история счета и исполнения -> восстановленные сделки -> метрики (FR-2).
3. Фильтры (FR-3), оценка с вкладом каждой метрики (FR-4), уверенность (FR-5), стиль (FR-6) -> вердикт с причинами (FR-7).

Все параметры методики лежат в `src/hl_trader/domain/methodology.py` и имеют номер версии.

## Запуск

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"

uv run hl-trader scan --top 20  # живой рейтинг -> отсев -> оценка 20 лучших кандидатов

docker compose up -d postgres
cp .env.example .env && export $(cat .env)
uv run hl-trader db-init  # схема БД

uv run pytest  # тесты названы по ID тест-кейсов RTM: pytest -k tc_
```
