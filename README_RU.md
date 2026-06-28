<div align="center">

<img src="assets/forreadme/logo2.png" alt="Баннер UrbanFlow AI" width="100%"/>

<br/>

<img src="assets/forreadme/logo.png" alt="Логотип UrbanFlow AI" width="300"/>

# UrbanFlow AI

[![Русский](https://img.shields.io/badge/README_Language-Русский-brightgreen)](https://github.com/TheAndreyZakharov/UrbanFlow-AI/blob/main/README_RU.md)
[![English](https://img.shields.io/badge/README_Language-English-blue)](https://github.com/TheAndreyZakharov/UrbanFlow-AI/blob/main/README.md)

</div>

UrbanFlow AI — это веб-приложение для 3D-симуляции городского трафика на реальных участках OpenStreetMap.

Проект импортирует реальные OSM-данные, строит 3D-сцену района в браузере, генерирует SUMO-сценарий, запускает микроскопическую транспортную симуляцию для автомобилей, пешеходов, автобусов, трамваев и другого общественного транспорта, а также позволяет AI-контроллеру управлять реальными SUMO-светофорами через TraCI.

Главная цель проекта — проверять, как реальная городская дорожная сеть ведет себя при разных транспортных нагрузках, дорожных событиях и стратегиях управления светофорами.

UrbanFlow AI объединяет:

- выбор участка OpenStreetMap;
- генерацию 3D-города на основе OSM;
- микроскопическую транспортную симуляцию SUMO;
- runtime-управление через TraCI;
- динамическое создание автомобилей;
- SUMO-пешеходов;
- маршруты и остановки общественного транспорта;
- редактор дорожных событий;
- инструменты принудительного управления светофорами;
- UrbanFlow AI контроллер светофоров;
- visual training;
- registry сохраненных моделей;
- live-метрики;
- генерируемые Jupyter notebooks и аналитику обучения.

Это технический, образовательный и исследовательский прототип для транспортной симуляции, urban planning workflows, AI-управления светофорами и интеграции с SUMO.

## Основная идея

UrbanFlow AI — это не декоративная анимация трафика.

3D-сцена является визуальным слоем поверх реальной SUMO-симуляции. Автомобили, пешеходы и общественный транспорт управляются SUMO. Светофоры являются реальными SUMO traffic lights. Если выбран режим SUMO automatic, сигналами управляет SUMO. Если выбран режим UrbanFlow AI, AI-контроллер меняет фазы SUMO-светофоров через TraCI, а SUMO-controlled автомобили продолжают подчиняться этим сигналам.

Frontend отображает состояние, которое приходит от backend. Backend управляет SUMO-сессией, импортом OSM, генерацией сценария, editor patches, training jobs и состоянием AI-контроллера.

## Как это работает

Схема обработки:

    Пользователь выбирает OSM-участок
              ↓
    Frontend отправляет bounding box на backend
              ↓
    Backend импортирует и нормализует OpenStreetMap данные
              ↓
    Backend строит SUMO-сценарий
              ↓
    SUMO запускает микроскопическую транспортную симуляцию
              ↓
    Автомобили, пешеходы и общественный транспорт двигаются в SUMO
              ↓
    React/Three.js frontend отображает 3D-город и участников движения
              ↓
    Светофорами управляет SUMO, fixed logic или UrbanFlow AI
              ↓
    Генерируются метрики, training artifacts и notebooks

UrbanFlow AI использует качество OpenStreetMap данных как основу для генерации города. В разных городах и районах уровень детализации может отличаться в зависимости от того, насколько полно они размечены сообществом OSM.

## Технологический стек

Frontend:

- React;
- Vite;
- TypeScript;
- React Leaflet;
- Three.js / React Three Fiber style architecture для 3D-сцены;
- браузерные UI-панели для симуляции, редактора, обучения и метрик.

Backend:

- FastAPI;
- Python;
- SUMO;
- TraCI;
- импорт и нормализация OSM;
- генерация SUMO-сценария;
- runtime simulation session store;
- AI training job store;
- registry JSON checkpoint моделей.

AI и аналитика:

- UrbanFlow AI runtime controller;
- JSON checkpoint policy;
- расчет reward из SUMO-метрик;
- visual training loop;
- генерируемый `training_history.csv`;
- генерируемый `training_history.jsonl`;
- генерируемые model checkpoints;
- Jupyter notebooks со встроенными графиками и таблицами.

## Текущий формат AI-модели

Текущая runtime-модель — это JSON checkpoint policy.

На данный момент это не PyTorch neural network, не ONNX model и не TorchScript model.

Активный runtime artifact:

    JSON checkpoint policy

ONNX и TorchScript export намеренно скрыты до подключения настоящей neural policy.

## Первый экран

При первом запуске приложение открывается с пустым 3D-workspace и навигационными элементами.

<div align="center">

<img src="assets/forreadme/1.png" alt="Первый экран UrbanFlow AI" width="600"/>

</div>

Центральная область предназначена для 3D-сцены города. До генерации участка пользователь видит приглашение открыть карту и выбрать реальный OSM-участок.

## Панель метрик и AI

Правая выдвижная панель содержит метрики симуляции, AI-статус, live-графики и registry моделей.

<div align="center">

<img src="assets/forreadme/2.png" alt="Панель метрик и AI в UrbanFlow AI" width="600"/>

</div>

Эта панель используется для просмотра:

- активных автомобилей;
- активных пешеходов;
- средней скорости;
- среднего времени ожидания;
- congestion score;
- остановившихся автомобилей;
- AI reward;
- статуса обучения;
- сохраненных моделей;
- live-графиков метрик.

## Выбор карты

Первая кнопка слева открывает OpenStreetMap selector.

<div align="center">

<img src="assets/forreadme/3.png" alt="Общий вид OpenStreetMap selector в UrbanFlow AI" width="600"/>

</div>

Карта открывается на широком world-level view.

Нижняя панель управления содержит:

- поле поиска города, улицы или района;
- размер стороны области в метрах;
- кнопки `+` и `-` для изменения размера области на 100 метров;
- действие поиска;
- действие подтверждения выбранной области.

После подтверждения выбранной области backend начинает импорт OSM-данных и генерацию SUMO-сценария.

## Поиск и выбор области

После ввода названия места карта фокусируется на найденной локации и приближается для выбора области.

<div align="center">

<img src="assets/forreadme/4.jpeg" alt="Выбранный OSM-участок после поиска в UrbanFlow AI" width="600"/>

</div>

Зеленый квадрат показывает выбранную область симуляции. Он определяет bounding box, который отправляется на backend.

Размер выбранной области можно изменить до генерации. Более крупные области могут содержать больше дорог, зданий и перекрестков, но требуют больше времени обработки и больше ресурсов симуляции.

## Экран генерации области

Во время импорта OSM и генерации сценария приложение показывает экран загрузки.

<div align="center">

<img src="assets/forreadme/5.jpeg" alt="Экран загрузки генерации области в UrbanFlow AI" width="600"/>

</div>

На этом этапе backend может выполнять несколько операций:

- импорт OSM-данных;
- нормализация OSM;
- генерация SUMO network;
- генерация routes и trips;
- генерация pedestrian trips;
- генерация public transport artifacts;
- проверка и исправление traffic-light references;
- создание simulation session.

## Сгенерированная 3D-сцена города

После генерации выбранная область появляется как 3D-сцена города.

<div align="center">

<img src="assets/forreadme/6.jpeg" alt="Сгенерированная 3D-сцена UrbanFlow AI" width="600"/>

</div>

По сцене можно перемещаться с помощью клавиатуры и мыши.

Управление:

- `W` — движение вперед;
- `S` — движение назад;
- `A` — движение влево;
- `D` — движение вправо;
- левая кнопка мыши — вращение камеры;
- правая кнопка мыши — перетаскивание/панорамирование вида.

Сцена отображает сгенерированный город, дороги, участников движения, события и дополнительные визуальные слои.

## Управление симуляцией

Панель Simulation настраивает активную SUMO-симуляцию.

<div align="center">

<img src="assets/forreadme/7.jpeg" alt="Панель управления симуляцией UrbanFlow AI" width="600"/>

</div>

Доступные элементы управления:

- play и pause;
- reset;
- скорость симуляции;
- количество автомобилей;
- количество пешеходов;
- режим управления светофорами;
- traffic-light override;
- OSM-only signals или all possible intersections;
- apply counts and signals.

Режимы управления светофорами:

- `SUMO automatic control` — SUMO управляет программами светофоров;
- `Manual fixed cycle` — простая fixed-cycle логика;
- `UrbanFlow AI control` — UrbanFlow AI загружает последнюю сохраненную JSON checkpoint модель и управляет SUMO-светофорами через TraCI.

Traffic-light override может принудительно применить один цвет ко всем управляемым светофорам для тестирования. Автомобили при этом остаются под управлением SUMO и реагируют на получившиеся состояния сигналов.

## Мосты, тоннели, остановки и видимость сигналов

3D-сцена поддерживает разные уровни дорог и transport-related элементы карты.

<div align="center">

<img src="assets/forreadme/8.png" alt="Мосты тоннели остановки и отключенное отображение всех сигналов в UrbanFlow AI" width="600"/>

</div>

Сцена может отображать:

- мосты;
- многоуровневые развязки;
- тоннели;
- остановки;
- инфраструктуру общественного транспорта;
- светофоры;
- цветовые индикаторы светофоров.

Цвет светофора также проецируется на небольшую платформу под сигналом, чтобы состояние было заметнее с камеры.

## Все перекрестки и принудительное состояние сигналов

Симуляцию можно перестроить или настроить так, чтобы светофоры были на всех возможных перекрестках.

<div align="center">

<img src="assets/forreadme/9.jpeg" alt="Все возможные светофоры UrbanFlow AI с принудительным зеленым сигналом" width="600"/>

</div>

Этот режим полезен для тестирования AI-управления на значительно большем количестве перекрестков.

Чтобы применить измененное количество участников или scope светофоров, используется действие `Apply counts and signals` в панели Simulation.

## Редактор дорог

Панель Editor позволяет применять дорожные события и изменения доступности дорог.

<div align="center">

<img src="assets/forreadme/10.png" alt="Панель редактора дорог UrbanFlow AI" width="600"/>

</div>

Поддерживаемые runtime-действия редактора:

- закрыть дорогу;
- открыть дорогу;
- roadwork;
- accident point;
- автоматические случайные дорожные события.

Текущее runtime-поведение:

- закрытые дороги запрещают движение автомобилей по выбранным SUMO edges;
- открытые дороги восстанавливают доступ;
- roadwork снижает допустимую скорость на выбранной дороге;
- accident points замедляют автомобили в локальном радиусе вокруг выбранной точки;
- автоматические события настраиваются по длительности и частоте.

## Закрытие дороги

Пользователь может выбрать дорогу и отметить ее как закрытую.

<div align="center">

<img src="assets/forreadme/11.jpeg" alt="Выбор дороги для закрытия в UrbanFlow AI" width="600"/>

</div>

Закрытая дорога становится недоступной для автомобильного движения. SUMO vehicles не используют ее как обычную drivable road.

## Открытие дороги

Редактор также может явно открыть выбранную дорогу.

<div align="center">

<img src="assets/forreadme/12.jpeg" alt="Выбор дороги для открытия в UrbanFlow AI" width="600"/>

</div>

Это полезно, когда дорога ранее была закрыта ручным событием или автоматическим сценарием.

## Roadwork

Roadwork применяет сниженное ограничение скорости к выбранной дороге.

<div align="center">

<img src="assets/forreadme/13.jpeg" alt="Выбор roadwork location в UrbanFlow AI" width="600"/>

</div>

В текущей реализации roadwork снижает скорость движения по сравнению с обычной OSM/SUMO скоростью дороги.

## Accident point

Accident point замедляет трафик рядом с выбранной точкой.

<div align="center">

<img src="assets/forreadme/14.png" alt="Выбор accident point в UrbanFlow AI" width="600"/>

</div>

Эффект аварии является локальным и применяется вокруг выбранной точки.

## Примененные события редактора

Редактор отображает примененные изменения прямо на городской сцене.

<div align="center">

<img src="assets/forreadme/15.jpeg" alt="Примененные события редактора дорог в UrbanFlow AI" width="600"/>

</div>

Визуальные значения:

- красные светящиеся дороги — вручную заблокированные дороги;
- зеленые дороги — явно открытые дороги;
- желтые светящиеся дороги — roadwork;
- оранжевые точки — accident locations;
- красные pedestrian-only дороги — пешеходный или недоступный для автомобилей доступ.

## Настройки отображения

Панель View управляет качеством сцены и визуальными слоями.

<div align="center">

<img src="assets/forreadme/16.jpeg" alt="Панель настроек отображения UrbanFlow AI" width="600"/>

</div>

Доступные настройки отображения:

- shadows;
- high resolution rendering;
- depth precision mode;
- fine geometry details;
- detailed actor models;
- building rendering;
- ground zone colors;
- special zones;
- road access highlight;
- congestion highlight.

Самые тяжелые визуальные функции можно отключить, чтобы симуляция работала быстрее.

## Минимальный режим отрисовки

Сцена может работать с легкими настройками рендера.

<div align="center">

<img src="assets/forreadme/17.png" alt="Минимальный режим отрисовки UrbanFlow AI вблизи" width="600"/>

</div>

Этот режим полезен для симуляции и обучения с приоритетом на производительность.

## Максимальная детализация

Сцена также может отображаться с большим количеством визуальных слоев и деталей.

<div align="center">

<img src="assets/forreadme/18.png" alt="Детализированный режим UrbanFlow AI общий план" width="600"/>

</div>

<div align="center">

<img src="assets/forreadme/19.png" alt="Детализированный режим UrbanFlow AI вблизи" width="600"/>

</div>

Детализированный режим может показывать больше зданий, зон, участников движения и геометрических деталей.

## Режимы визуализации участников движения

Автомобили могут отображаться в более простом или более детализированном виде в зависимости от требований к производительности и визуализации.

<table>
<tr>
<td align="center">
<img src="assets/forreadme/20.png" alt="Простая модель автомобиля UrbanFlow AI" width="400"/>
</td>
<td align="center">
<img src="assets/forreadme/21.png" alt="Детализированная модель автомобиля UrbanFlow AI" width="400"/>
</td>
</tr>
</table>

Пешеходы также поддерживают детализированный режим отображения.

<div align="center">

<img src="assets/forreadme/22.png" alt="Детализированная модель пешехода UrbanFlow AI" width="600"/>

</div>

В простом режиме пешеходы могут отображаться как легкие маркеры. В детализированном режиме они показываются с более подробной визуальной структурой.

## Визуализация доступности дорог

Road access highlighting показывает, какие части сети доступны или ограничены.

<div align="center">

<img src="assets/forreadme/23.jpeg" alt="Общий план визуализации доступности дорог UrbanFlow AI" width="600"/>

</div>

<div align="center">

<img src="assets/forreadme/24.png" alt="Крупный план визуализации доступности дорог UrbanFlow AI" width="600"/>

</div>

Типичные цвета:

- pedestrian-only дороги и пути отображаются красным;
- вручную закрытые дороги имеют более сильную красную подсветку;
- roadwork отображается желтой подсветкой;
- accident locations отображаются желтыми/оранжевыми точками.

## Визуализация загруженности

Congestion highlighting показывает транспортную нагрузку на дорогах.

<div align="center">

<img src="assets/forreadme/25.jpeg" alt="Общий план визуализации загруженности дорог UrbanFlow AI" width="600"/>

</div>

<div align="center">

<img src="assets/forreadme/26.png" alt="Крупный план визуализации загруженности дорог UrbanFlow AI" width="600"/>

</div>

Типичные цвета загруженности:

- зеленый — свободное движение;
- желтый — средняя нагрузка;
- красный — высокая нагрузка.

## Панель AI training

Панель Training настраивает visual training для UrbanFlow AI controller.

<div align="center">

<img src="assets/forreadme/27.jpeg" alt="Панель обучения UrbanFlow AI" width="600"/>

</div>

Настройки обучения:

- signal scope;
- только OSM traffic lights;
- все возможные перекрестки;
- стартовое количество автомобилей;
- максимальное количество автомобилей;
- vehicle step;
- steps per level;
- количество пешеходов;
- random road events during training;
- start visual training;
- stop training;
- save trained model;
- export checkpoint.

Процесс обучения выполняется на активной SUMO-сессии. SUMO продолжает управлять движением автомобилей и пешеходов. UrbanFlow AI управляет только решениями по фазам светофоров.

## Процесс visual training

Во время обучения симуляция продолжает визуально работать, а метрики обновляются.

<div align="center">

<img src="assets/forreadme/28.jpeg" alt="Процесс visual training в UrbanFlow AI" width="600"/>

</div>

Training job записывает:

- current step;
- current episode;
- current vehicle count;
- best reward;
- latest reward;
- average waiting time;
- congestion score;
- stopped vehicles;
- checkpoint path;
- training run directory.

Когда checkpoint доступен, модель можно сохранить в model registry.

## Общественный транспорт

UrbanFlow AI поддерживает public transport artifacts и runtime vehicles, когда SUMO может построить валидные маршруты из OSM-данных.

Поддержка общественного транспорта включает:

- автобусные остановки;
- автобусные маршруты;
- маршруты троллейбусов/маршруток в случаях, когда они представлены как совместимые дорожные маршруты OSM;
- трамвайные маршруты;
- движение трамваев по rail/tram edges, если в SUMO network есть валидные rail/tram участки;
- public transport vehicles, которые следуют своим маршрутам;
- использование остановок, если они были валидно сгенерированы.

Общественный транспорт не является фейковым визуальным слоем. Если transport vehicle успешно создан, он является SUMO/TraCI vehicle и следует SUMO-маршруту.

## Режимы симуляции

### SUMO automatic control

SUMO управляет светофорами через собственные signal programs.

Автомобили, пешеходы и общественный транспорт при этом остаются SUMO-симуляцией.

### Manual fixed cycle

Приложение применяет простую fixed-cycle стратегию управления светофорами.

Этот режим используется как baseline.

### UrbanFlow AI control

UrbanFlow AI управляет реальными SUMO-светофорами через TraCI.

При выборе этого режима backend пытается загрузить последнюю сохраненную модель для текущего signal scope. Если сохраненной модели нет, runtime controller использует default JSON policy.

## AI observations и решения

Для каждого управляемого SUMO traffic light UrbanFlow AI может наблюдать:

- controlled lanes;
- текущую фазу;
- доступные phases;
- количество автомобилей;
- количество остановившихся автомобилей;
- среднюю скорость;
- максимальную скорость;
- waiting time;
- occupancy;
- allowed и disallowed vehicle classes;
- pressure текущей фазы;
- pressure candidate phases.

Контроллер может:

- оставить текущую фазу;
- переключиться на другую green phase;
- избегать слишком частых переключений;
- соблюдать minimum green time;
- реагировать на высокий lane pressure;
- реагировать на чрезмерно долгую активность текущей фазы.

## Reward

Текущая reward-функция рассчитывается из traffic metrics, полученных из SUMO.

Она может включать:

- queue penalty;
- waiting-time penalty;
- stopped-vehicle penalty;
- congestion penalty;
- low-speed penalty;
- phase-switch penalty;
- throughput bonus.

Цель — уменьшать ожидание, очереди, congestion и избегать хаотичного переключения светофоров.

## Training artifacts и сохраненные модели

Training artifacts записываются в:

    data/models/

Типичная структура:

    data/models/tls_osm_only/
      runs/
        training_<id>/
          job.json
          training_history.csv
          training_history.jsonl
          latest_summary.json
          training_dashboard.md
          notebook_refresh.log
          checkpoints/
            best_model.json
          snapshots/
            checkpoint_step_00000120.json
      saved/
        model_<id>_training_<id>_step_00000150.json
        model_<id>_training_<id>_step_00000150.metadata.json
      exports/
        export_<id>_training_<id>_step_00000150.json
        export_<id>_training_<id>_step_00000150.metadata.json

Для all-intersections scope artifacts хранятся в:

    data/models/tls_all_intersections/

Действие `Save trained model` копирует лучший checkpoint в registry сохраненных моделей.

Действие `Export checkpoint` создает дополнительный checkpoint export для анализа или переноса.

## Генерируемые notebooks

UrbanFlow AI генерирует Jupyter notebooks со встроенными outputs.

Файлы notebooks:

    ai/notebooks/01_explore_sumo_tls.ipynb
    ai/notebooks/02_reward_design.ipynb
    ai/notebooks/03_train_tls_agent.ipynb
    ai/notebooks/04_evaluate_tls_agent.ipynb

Notebooks могут показывать:

- количество SUMO artifacts;
- parsed debug metrics;
- traffic-light statistics;
- intersection complexity;
- reward sensitivity;
- reward surface;
- training history;
- rolling reward;
- графики average waiting time;
- графики congestion;
- графики stopped vehicles;
- checkpoint summaries;
- данные saved model registry.

Notebook generator можно запустить вручную:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/server && uv run python ../ai/notebooks/create_analysis_notebooks.py

Training artifact writer также может автоматически обновлять notebooks с throttle.

## Локальная разработка

Проект предназначен для запуска из исходного кода во время разработки.

Установить backend dependencies:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/server && uv sync

Установить frontend dependencies:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/web && npm install

Запустить development environment:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI && ./scripts/run-dev.sh

Открыть frontend:

    http://127.0.0.1:5173

Команда для очистки занятых портов:

    for port in 8000 8080 5173; do lsof -tiTCP:$port -sTCP:LISTEN | xargs kill -9 2>/dev/null || true; done

Проверка сборки frontend:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/web && npm run build

Проверка компиляции backend:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/server && uv run python -m py_compile app/simulation/sumo_engine.py app/simulation/sumo_scenario.py app/simulation/training_jobs.py app/simulation/ai_tls_controller.py

Проверка импортов AI package:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI && PYTHONPATH=ai python3 -m py_compile ai/urbanflow_ai/integration/runtime_controller.py ai/urbanflow_ai/env/sumo_tls_env.py ai/urbanflow_ai/models/policy.py

## Структура проекта

    UrbanFlow-AI/
    ├── ai/
    │   ├── notebooks/
    │   │   ├── 01_explore_sumo_tls.ipynb
    │   │   ├── 02_reward_design.ipynb
    │   │   ├── 03_train_tls_agent.ipynb
    │   │   ├── 04_evaluate_tls_agent.ipynb
    │   │   └── create_analysis_notebooks.py
    │   └── urbanflow_ai/
    │       ├── analysis/
    │       │   └── Training artifacts и notebook refresh utilities
    │       ├── env/
    │       │   └── SUMO TLS environment, observations, actions и rewards
    │       ├── evaluation/
    │       │   └── Evaluation helpers
    │       ├── export/
    │       │   └── Checkpoint export helpers
    │       ├── integration/
    │       │   └── Runtime controller, используемый backend
    │       ├── models/
    │       │   └── JSON policy и checkpoint logic
    │       ├── training/
    │       │   └── Curriculum и training helpers
    │       └── utils/
    │           └── Network metric utilities
    ├── assets/
    │   └── forreadme/
    │       └── README logos и screenshots
    ├── data/
    │   ├── models/
    │   │   ├── tls_osm_only/
    │   │   └── tls_all_intersections/
    │   ├── osm/
    │   ├── runs/
    │   └── sessions/
    ├── docs/
    │   └── urbanflow-ai-spec.md
    ├── scripts/
    │   ├── run-dev.sh
    │   ├── run-server.sh
    │   ├── run-web.sh
    │   ├── test-server.sh
    │   └── test-web.sh
    ├── server/
    │   ├── app/
    │   │   ├── api/
    │   │   │   └── FastAPI routes для OSM, simulation, editor и training
    │   │   ├── core/
    │   │   │   └── Backend configuration
    │   │   ├── osm/
    │   │   │   └── OSM client, parser и normalizer
    │   │   ├── schemas/
    │   │   │   └── Pydantic schemas
    │   │   ├── simulation/
    │   │   │   └── SUMO engine, TraCI control, metrics, events и training jobs
    │   │   └── utils/
    │   │       └── Geo utilities
    │   ├── pyproject.toml
    │   └── uv.lock
    ├── tests/
    │   ├── server/
    │   └── web/
    └── web/
        ├── src/
        │   ├── api/
        │   │   └── API client
        │   ├── components/
        │   │   └── UI panels и controls
        │   ├── scene/
        │   │   └── 3D city scene и actors
        │   ├── styles/
        │   │   └── Global CSS
        │   ├── types/
        │   │   └── Domain и scene types
        │   └── utils/
        │       └── Formatting utilities
        ├── package.json
        └── vite.config.ts

## Примечания

UrbanFlow AI сфокусирован на реальном поведении симуляции, а не на чисто визуальной анимации.

Важные особенности реализации:

- SUMO управляет движением автомобилей;
- SUMO управляет движением пешеходов;
- SUMO управляет движением общественного транспорта, если маршруты валидны;
- автомобили подчиняются SUMO-светофорам;
- UrbanFlow AI управляет только фазами светофоров, когда выбран AI mode;
- fixed/manual algorithms также управляют светофорами через simulation layer;
- автомобили остаются SUMO-controlled в любом режиме управления светофорами;
- качество OSM-данных влияет на сгенерированные дороги, здания, маршруты и общественный транспорт;
- не каждый OSM-участок содержит достаточно данных по светофорам, общественному транспорту или зданиям.

Проект является рабочим техническим прототипом и основой для дальнейших экспериментов в области транспортной симуляции, AI control, urban analytics и reinforcement learning.