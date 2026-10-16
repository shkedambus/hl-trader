# Исследование

## Данные HyperLiquid

- [Info endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint): все нужные данные публичны и доступны без авторизации. Для отбора используются `portfolio` (история стоимости счета и PnL, десятки точек за жизнь счета) и `userFillsByTime` (исполнения, до 2 000 за ответ, с полем `startPosition`, по которому восстанавливаются сделки). Позже для отслеживания понадобится `clearinghouseState`.
- [Лимиты](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits): 1 200 единиц веса в минуту на IP. `portfolio` стоит 20, `userFillsByTime` стоит 20 плюс 1 за каждые 20 исполнений в ответе. Поэтому отбор идет от бесплатных данных к платным, а лимитер берет вес из общего бюджета 1 100 в минуту (NFR-2).
- Публичный рейтинг ([интерфейс](https://app.hyperliquid.xyz/leaderboard), [выгрузка](https://stats-data.hyperliquid.xyz/Mainnet/leaderboard)) отдается обычным GET и вес не тратит. На 16.10.2026 в нем 47 334 аккаунта, после предварительного отсева (SRS, А.1) остается 5 445.
- В исполнении есть отметка о ликвидации, но она может относиться к контрагенту. Ликвидация засчитывается трейдеру, только если `liquidatedUser` совпадает с его адресом (FR-2, TC-2.3).

## Метрики

- Доходность с поправкой на риск (Шарп) считается по интервалам истории счета. Депозиты и выводы исключаются [модифицированным методом Дитца](https://en.wikipedia.org/wiki/Modified_Dietz_method). Точки идут неравномерно, поэтому к году Шарп приводится по их фактическому среднему интервалу.
- Просадка считается по тому же индексу доходности: по стоимости счета вывод средств выглядел бы как просадка.

## Конкуренты

- [Hyperdash](https://hyperdash.info), [Nansen](https://www.nansen.ai): оценка трейдеров есть, формула закрыта.
- [Copin](https://copin.io): открытые фильтры, итоговой оценки нет.
- Ни один не показывает, на скольких сделках построен вывод, и не объясняет отказ. В hl-trader для этого есть мера уверенности и карточка с причинами.

## MCP

- [Model Context Protocol](https://modelcontextprotocol.io), [Python SDK](https://github.com/modelcontextprotocol/python-sdk).
- Существующие MCP-серверы HyperLiquid ([edkdev](https://github.com/edkdev/hyperliquid-mcp), [midodimori](https://glama.ai/mcp/servers/midodimori/hyperliquid-mcp)) дают цены, стакан и ордера, но не умеют искать трейдеров.

## Стек

Python 3.12, asyncio, [httpx](https://www.python-httpx.org), [aiolimiter](https://github.com/mjpieters/aiolimiter) для лимита веса, PostgreSQL ([psycopg 3](https://www.psycopg.org/psycopg3/)), далее FastAPI, [aiogram](https://docs.aiogram.dev) и MCP SDK.
