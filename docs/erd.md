# Модель данных

Схема: [`src/hl_trader/storage/schema.sql`](../src/hl_trader/storage/schema.sql). Сплошные линии обозначают внешние ключи, пунктирные показывают связь по адресу трейдера или `chat_id` без внешнего ключа.

```mermaid
erDiagram
    methodology_versions ||--o{ verdicts : "версия методики"
    trader_metrics ||--o{ verdicts : "по метрикам"
    candidates ||..o{ trader_metrics : "address"
    verdicts ||..o{ positions : "отслеживаемые"
    verdicts ||..o{ events : "address"
    events ||--o{ deliveries : "доставлено"
    subscriptions ||..o{ deliveries : "chat_id"
    verdicts ||..o{ subscriptions : "address"

    methodology_versions {
        text version PK
        jsonb parameters "пороги, веса, границы (А.1-А.6)"
        timestamptz effective_at
    }

    candidates {
        text address PK
        timestamptz first_seen
        timestamptz last_refreshed
        numeric account_value
        numeric pnl_all_time
        float roi_all_time
        numeric volume_all_time
        float priority "очередь платных запросов"
    }

    trader_metrics {
        bigint id PK
        text address UK "UNIQUE (address, computed_at)"
        timestamptz computed_at UK
        float window_days
        float tenure_days
        numeric account_value
        float sharpe "NULL = нет данных"
        float max_drawdown
        int portfolio_points
        int round_trips
        float win_rate
        float profit_factor
        float expectancy_pct
        float median_hold_s
        int fills_count
        float fills_per_day
        bool fills_truncated
        float liquidated_share
        text_array coins
    }

    verdicts {
        bigint id PK
        text address
        bigint metrics_id FK
        text methodology_version FK
        timestamptz judged_at
        bool selected
        bool is_tracked "топ-N"
        float score
        float confidence
        text style
        jsonb contributions "вклад метрик в оценку"
        jsonb checks "фильтры и пороги: факт, порог"
    }

    positions {
        text address PK
        text coin PK
        text direction
        numeric size
        numeric notional
        numeric leverage
        numeric entry_px
        timestamptz observed_at
    }

    events {
        bigint id PK "курсор доставки"
        text address
        text kind "position | review"
        text event_type
        timestamptz occurred_at
        jsonb payload
    }

    subscriptions {
        bigint chat_id PK "только chat id (NFR-7)"
        text address PK
        timestamptz created_at
    }

    deliveries {
        bigint event_id PK,FK
        bigint chat_id PK "ровно один раз (NFR-6)"
        timestamptz delivered_at
    }
```

## Как читать

Отбор (FR-1...FR-8) идет через `candidates`, `trader_metrics` и `verdicts`. Метрики и вердикты только дописываются (NFR-4). При смене методики пересчет добавляет вердикты новой версии по тем же `metrics_id` и к бирже не обращается.

Для отслеживания (FR-9, FR-10) в `positions` хранится последнее состояние трейдеров с `is_tracked`. Каждое изменение позиции пишется в `events`, туда же попадает пересмотр вывода (`kind = review`).

Для доставки (FR-14...FR-16) `subscriptions` связывает чат с трейдером, а первичный ключ `deliveries` не дает отправить одно событие в один чат дважды.
