# Идентификация пользователя по сетевым сессиям

Курсовая работа по теме: **«Идентификация и верификация пользователя при использовании VPN/Proxy на основе поведенческой биометрии и временных сетевых сессий».**

Пайплайн разбивает flow-записи на пользовательские сессии, извлекает признаки и распознаёт пользователя гибридным методом: классификатор + индивидуальный детектор аномалий (IsolationForest) на каждого пользователя.

## Модели

| Модуль | Модель | Назначение |
|---|---|---|
| `modeling.py` | `CatBoostClassifier` / `RandomForestClassifier` | Классификатор пользователя |
| `modeling.py` | `IsolationForest` (на пользователя) | Детектор аномалий (open-set) |
| `iscx_vpn.py` | `RandomForestClassifier` (400 деревьев) | VPN/non-VPN классификация |

Модели не хранятся в репозитории — они воспроизводятся скриптом обучения (см. ниже).

Структура артефактов после обучения:

```
artifacts/
    demo/                        <- идентификация пользователя
        threshold_60m/
        threshold_30m/
        threshold_comparison.csv
    iscx_vpn/
        15s/model.joblib         <- VPN/non-VPN, окно 15s
        30s/model.joblib
        60s/model.joblib
        120s/model.joblib
        metrics_comparison.csv
```

## Требования

- Python 3.10+
- pip

## Как запустить

1. Клонируйте репозиторий:

```bash
git clone https://github.com/username/repo.git
cd repo
```

2. Запустите скрипт установки — он установит зависимости и обучит все модели:

**Windows:**
```
setup.bat
```

**Linux / Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

Скрипт выполняет три шага автоматически:
- устанавливает зависимости из `requirements.txt`;
- пробует установить CatBoost (если не выйдет — используется RandomForest);
- обучает все модели и сохраняет артефакты в `artifacts/`.

Если нужно обучить вручную или с реальным датасетом:

```bash
# вручную
pip install -r requirements.txt
python scripts/train_all.py

# с реальным CSV пользователей
python scripts/train_all.py --input-csv data/flows.csv
```

## Запуск на своём датасете

```bash
python scripts/run_demo.py --input-csv data/flows.csv --output-dir artifacts/real_run
```

Формат CSV — обязательные столбцы:

| Столбец | Описание |
|---|---|
| `user_id` | Идентификатор пользователя |
| `mode` | Режим трафика (`direct` / `vpn`) |
| `start_time`, `end_time` | Временные метки flow |
| `duration` | Длительность (сек) |
| `bytes_up`, `bytes_down` | Байты вверх/вниз |
| `pkts_up`, `pkts_down` | Пакеты вверх/вниз |

Дополнительные признаки (если есть): `flow_iat_*`, `fwd_iat_*`, `bwd_iat_*`, `active_*`, `idle_*`, `bytes_per_sec`, `pkts_per_sec`.

По умолчанию сессия закрывается при паузе > 60 минут; эксперимент также проверяет порог 30 минут.

## VPN/non-VPN классификация на ISCX

ARFF-файлы помещаются в `data/`, затем:

```bash
python scripts/run_iscx_vpn.py --data-dir data --output-dir artifacts/iscx_vpn
```

Скрипт обрабатывает файлы с окнами `15s`, `30s`, `60s`, `120s`.

## Proxy-эксперимент идентификации на ISCX

Классы приложений (`BROWSING`, `VOIP`, `CHAT` и т.д.) используются как proxy-идентичности:

```bash
python scripts/run_iscx_userid_proxy.py --input-arff data/TimeBasedFeatures-Dataset-15s.arff --output-dir artifacts/iscx_userid_proxy
```

> Результаты нельзя интерпретировать как точность идентификации реальных пользователей — это proxy-постановка из-за отсутствия `user_id` в датасете.

## Проверка сохранённой модели ISCX

```bash
python scripts/predict_iscx_vpn.py --model artifacts/iscx_vpn/15s/model.joblib --input-arff data/TimeBasedFeatures-Dataset-15s.arff --output-csv artifacts/iscx_vpn/manual_test_predictions.csv
```

## Результаты

**Основной эксперимент** (`artifacts/demo/` или `artifacts/real_run/`):

- `session_features.csv` — признаки сессий
- `metrics.json` — итоговые метрики
- `predictions_<scenario>.csv` — предсказания
- матрица ошибок, ROC-кривая, график метрик по сценариям

**ISCX VPN/non-VPN** (`artifacts/iscx_vpn/<окно>/`):

- `metrics_comparison.csv`, `metrics_summary.csv`
- `predictions.csv`, `feature_importance.csv`
- `model.joblib` — сохранённая модель
- графики: confusion matrix, ROC, precision-recall, важность признаков, корреляции, распределения
