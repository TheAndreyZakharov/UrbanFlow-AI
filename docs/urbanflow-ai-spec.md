# UrbanFlow AI

**UrbanFlow AI** — веб-приложение для 3D-симуляции городского трафика на реальных участках OpenStreetMap.  
Пользователь выбирает участок города, система импортирует OSM-данные, строит 3D-сцену района, запускает микроскопическую SUMO-симуляцию машин, пешеходов и общественного транспорта, а UrbanFlow AI управляет реальными SUMO-светофорами через TraCI, чтобы снижать ожидание, пробки и перегруженность перекрестков.

---

## 1. Главная идея

UrbanFlow AI — это смесь:

- реального города из OpenStreetMap;
- 3D-визуализации района в браузере;
- микроскопической транспортной симуляции SUMO;
- редактора дорожных сценариев;
- AI-контроллера для управления светофорами;
- visual training режима;
- registry сохраненных моделей;
- автоматической аналитики и notebook-отчетов.

Цель продукта — дать возможность быстро проверить, как работает дорожная сеть района, где возникают проблемы и как адаптивное управление светофорами может улучшить транспортный поток.

---

## 2. Пользовательский сценарий

1. Пользователь открывает веб-приложение.
2. Открывает карту.
3. Выбирает город или конкретный участок.
4. Задает размер области симуляции.
5. UrbanFlow AI загружает реальные данные из OpenStreetMap.
6. Система строит 3D-город:
   - дороги;
   - перекрестки;
   - здания;
   - поверхности;
   - пешеходные переходы;
   - остановки;
   - общественный транспорт;
   - светофоры;
   - инфраструктуру.
7. Backend создает SUMO-сценарий:
   - OSM XML;
   - SUMO network;
   - маршруты;
   - pedestrian trips;
   - public transport stops/routes;
   - debug artifacts.
8. Пользователь запускает симуляцию.
9. SUMO управляет движением машин, пешеходов и общественного транспорта.
10. Пользователь может включить режим UrbanFlow AI.
11. AI-контроллер меняет фазы реальных SUMO-светофоров через TraCI.
12. Пользователь видит метрики, графики, reward, ожидание, скорость и congestion.
13. После visual training пользователь сохраняет модель.
14. При выборе режима UrbanFlow AI система автоматически загружает последнюю сохраненную модель для текущего scope.

---

## 3. Визуальный стиль

Графика должна быть 3D, но не фотореалистичной.

Стиль:

- low-poly;
- чистый;
- понятный;
- быстрый для браузера;
- похожий на urban planning / city simulation tools;
- вид сверху под углом;
- плавная камера;
- читаемые дороги и перекрестки;
- цветовая индикация транспорта, событий и загруженности;
- без перегруза деталями.

Главная цель — чтобы симуляция выглядела как настоящий мини-город, но оставалась производительной.

---

## 4. 3D-город из OpenStreetMap

После выбора участка система строит городскую сцену по OSM-данным.

### Дороги

Отображаются:

- основные дороги;
- второстепенные дороги;
- жилые улицы;
- service roads;
- односторонние дороги;
- перекрестки;
- повороты;
- развязки;
- пешеходные переходы;
- остановки;
- участки общественного транспорта;
- ограничения движения, если они есть в OSM.

Дороги повторяют реальные формы из OSM.

### Здания

Здания строятся по контурам из OSM.

Учитывается:

- форма здания;
- высота, если указана;
- количество этажей, если указано;
- тип здания, если указан;
- базовая визуальная категория.

Если высота не указана, система может использовать приблизительную высоту по типу здания.

### Инфраструктура

На карте отображаются или используются в данных:

- светофоры;
- остановки;
- переходы;
- парковки;
- школы;
- больницы;
- магазины;
- офисы;
- станции транспорта;
- парки;
- площади;
- общественные объекты;
- tram/rail lines, если они есть в OSM.

---

## 5. Транспортная симуляция

UrbanFlow AI использует SUMO как реальный микроскопический симулятор транспорта.

Это значит, что движение не является декоративной анимацией. Машины, пешеходы и транспортные средства существуют в SUMO и управляются правилами SUMO.

### Машины

В симуляции есть:

- легковые автомобили;
- такси;
- автобусы;
- грузовики;
- экстренные службы;
- служебные/доставочные машины, если тип разрешен дорожной сетью.

У машин есть:

- SUMO-маршрут;
- скорость;
- ускорение;
- торможение;
- реакция на светофоры;
- реакция на пробки;
- реакция на закрытые дороги;
- lane logic;
- визуальная модель;
- цвет;
- положение из TraCI.

Машины создаются динамически через TraCI. Система подбирает реальные SUMO edges, ищет маршрут через `simulation.findRoute`, добавляет route и запускает vehicle в SUMO.

### Пешеходы

Пешеходы генерируются через SUMO pedestrian/person trips.

Пешеходы:

- двигаются внутри SUMO;
- появляются в визуальной сцене через TraCI;
- имеют координаты, скорость и направление;
- визуально отображаются в 3D-сцене;
- учитываются в метриках и intersection load.

### Общественный транспорт

Система поддерживает public transport artifacts и runtime-spawn:

- автобусные остановки;
- train/tram stops;
- bus routes;
- tram routes, если их можно построить по OSM/SUMO данным;
- public transport vehicles через TraCI.

Если маршрут общественного транспорта невозможно безопасно построить, система не создает фейковый fallback, а пропускает такой маршрут.

### Коллизии и правила движения

Коллизии и дорожное поведение отвечает SUMO:

- машина не должна ехать сквозь другую машину;
- транспорт учитывает светофоры;
- транспорт учитывает lane permissions;
- транспорт не должен стартовать на запрещенной lane;
- закрытые дороги запрещаются через TraCI;
- маршруты пересчитываются или транспорт удаляется, если дорога стала недоступной;
- пешеходы и транспорт двигаются по SUMO-сценарию.

---

## 6. События и редактор сценариев

Система поддерживает события, которые меняют трафик.

Примеры событий:

- авария;
- roadwork;
- закрытие дороги;
- открытие дороги;
- временное ограничение скорости;
- traffic boost;
- attraction point;
- очистка события.

События нужны, чтобы проверять устойчивость городской сети и AI-контроллера к нестабильным условиям.

### Текущая реализация событий

- `close_road` закрывает связанные SUMO edges через `lane.setDisallowed`.
- `open_road` возвращает движение.
- `roadwork` снижает max speed lane через TraCI.
- `accident` ограничивает скорость транспорта рядом с событием.
- Random events могут включаться во время simulation/training.
- Editor patches сохраняются в состоянии сессии.

---

## 7. AI-система

AI отвечает за адаптивное управление светофорами.

Текущая runtime-реализация UrbanFlow AI — это JSON-checkpoint policy/controller, который работает поверх SUMO через TraCI.

Он:

- читает реальные SUMO traffic lights;
- собирает lane-level observations;
- считает давление/pressure по очередям, ожиданию, скорости, occupancy и emergency-priority;
- выбирает фазу светофора;
- применяет `trafficlight.setPhase`;
- задает duration через TraCI;
- считает reward;
- сохраняет checkpoint/state в JSON.

Важно: текущая активная модель — это не PyTorch neural network и не ONNX/TorchScript. Поэтому ONNX и TorchScript export скрыты. Рабочий runtime artifact сейчас — JSON checkpoint.

---

## 8. AI-контроллер перекрестка

Для каждого управляемого SUMO TLS контроллер собирает наблюдения.

Он наблюдает:

- controlled lanes;
- текущую фазу светофора;
- список доступных phases;
- количество машин на lane;
- количество остановившихся машин;
- среднюю скорость;
- max speed;
- waiting time;
- occupancy;
- allowed/disallowed vehicle classes;
- pressure текущей фазы;
- pressure альтернативных фаз.

Он принимает решения:

- удерживать текущую фазу;
- переключиться на другую green phase;
- не переключаться слишком часто;
- соблюдать minimum green time;
- переключиться при сильном pressure;
- переключиться по timeout, если текущая фаза слишком долго активна.

---

## 9. Общая AI-логика района

Сейчас UrbanFlow AI управляет всеми доступными SUMO traffic lights в рамках текущей simulation session.

Система поддерживает два scope:

### OSM traffic lights only

Используются только светофоры, которые пришли из OSM/SUMO network.

### All possible intersections

Система пытается построить сеть так, чтобы светофоры были на большем количестве перекрестков. Это используется для режима, где AI может управлять максимальным числом intersections.

Перспективная цель — развить это в полноценную multi-agent / graph-based систему, где:

- перекрестки = nodes;
- дороги = edges;
- транспортные потоки = edge features;
- светофоры = controllable nodes;
- соседние перекрестки влияют друг на друга.

Текущая версия уже управляет множеством SUMO TLS, но полноценная GNN/multi-agent neural architecture еще не является основной runtime-моделью.

---

## 10. За что отвечает AI

AI отвечает за:

- уменьшение очередей;
- уменьшение среднего ожидания;
- уменьшение congestion score;
- уменьшение количества остановившихся машин;
- повышение средней скорости;
- адаптацию фаз светофоров к текущей SUMO-ситуации;
- работу с реальными SUMO traffic lights;
- сбор reward;
- сохранение checkpoint;
- применение последней сохраненной модели.

---

## 11. За что AI не отвечает

AI не отвечает за то, что правильно делает SUMO или обычные алгоритмы.

Алгоритмами и SUMO делается:

- загрузка OSM;
- построение дорожного графа;
- генерация SUMO network;
- генерация 3D-геометрии;
- базовое движение машин;
- поведение машин;
- поиск маршрутов;
- движение пешеходов;
- остановки и маршруты общественного транспорта;
- lane permissions;
- физика дорожного движения;
- рендеринг;
- редактор карты;
- расчет базовых метрик.

AI нужен именно для принятия решений по светофорам в динамической дорожной среде.

---

## 12. Обучение модели

В текущей версии обучение реализовано как visual training поверх реальной running SUMO session.

На каждом шаге:

1. SUMO-сессия работает.
2. UrbanFlow AI получает observations по traffic lights и lanes.
3. AI выбирает действия для светофоров.
4. Действия применяются через TraCI.
5. SUMO делает simulation step.
6. Система считает метрики.
7. Система считает reward.
8. Training job сохраняет runtime metrics.
9. При улучшении или по интервалу пишется checkpoint.
10. Генерируются training artifacts и notebooks.

Reward учитывает:

- queue penalty;
- waiting time penalty;
- stopped vehicles penalty;
- congestion penalty;
- low speed penalty;
- switch penalty;
- throughput bonus.

Штрафы:

- длинные очереди;
- большое ожидание;
- много остановившихся машин;
- высокая congestion score;
- слишком частые переключения фаз;
- низкая скорость движения.

---

## 13. Training artifacts и сохранение моделей

При visual training система создает artifacts в проектной папке `data/models`.

Структура:

```text
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
```

Для режима all intersections используется отдельный scope:

```text
data/models/tls_all_intersections/
```

### Save trained model

Кнопка **Save trained model** копирует лучший checkpoint текущего training job в registry сохраненных моделей.

### Export checkpoint

Кнопка **Export checkpoint** создает дополнительную копию checkpoint для анализа/переноса.

### Автозагрузка модели

Когда пользователь выбирает режим **UrbanFlow AI control**, backend автоматически ищет последнюю сохраненную модель в текущем scope:

- `tls_osm_only/saved`;
- или `tls_all_intersections/saved`.

Если модель найдена, она загружается в runtime controller. Если сохраненной модели нет, используется default runtime policy.

---

## 14. Автоматические notebooks и аналитика

UrbanFlow AI генерирует Jupyter notebooks с уже встроенными outputs.

Файлы:

```text
ai/notebooks/01_explore_sumo_tls.ipynb
ai/notebooks/02_reward_design.ipynb
ai/notebooks/03_train_tls_agent.ipynb
ai/notebooks/04_evaluate_tls_agent.ipynb
```

Они показывают:

- SUMO artifacts;
- parsed debug metrics;
- traffic light statistics;
- lane/intersection complexity;
- reward sensitivity;
- reward surface;
- training history;
- rolling reward;
- wait/congestion/stopped vehicles charts;
- checkpoint summaries;
- saved model registry;
- comparison charts.

Notebook generator запускается вручную или автоматически из training artifacts с throttle.  
Кодовые ячейки скрыты, а графики и таблицы уже встроены в `.ipynb`.

---

## 15. Режимы симуляции

### Manual fixed cycle

Режим с фиксированной логикой переключения фаз. Используется как простой baseline/manual mode.

### SUMO automatic control

SUMO управляет traffic lights своими программами.

### UrbanFlow AI control

UrbanFlow AI управляет реальными SUMO traffic lights через TraCI.  
При включении режима backend загружает последнюю saved модель для текущего scope, если она есть.

---

## 16. Compare / аналитическое сравнение

Система показывает метрики, по которым можно сравнивать режимы:

- средняя скорость;
- среднее ожидание;
- congestion score;
- stopped vehicles;
- active vehicles;
- active pedestrians;
- reward;
- history графики.

Полноценный автоматический benchmark “одна и та же зона в нескольких режимах с одинаковым seed и отчетом до/после” является следующим логичным этапом развития.

---

## 17. Редактор города

В приложении есть режим редактора.

Пользователь может изменять дорожную ситуацию поверх OSM/SUMO-сценария.

### Возможности редактора

Поддерживаются или заложены в API:

- закрыть дорогу;
- открыть дорогу;
- убрать дорогу как сценарий закрытия;
- добавить roadwork;
- добавить accident;
- traffic boost;
- attraction point;
- clear event;
- добавить переход;
- добавить светофор;
- удалить/изменить объект сценария.

Текущая runtime-часть надежно работает с тем, что возможно изменить в запущенной SUMO-сессии через TraCI.  
Создание полноценного нового светофора на уже запущенной SUMO network ограничено возможностями SUMO: для этого обычно нужно перестраивать network.

Редактор нужен для двух целей:

1. Исправлять или компенсировать неточности OSM.
2. Моделировать сценарии “что если”.

---

## 18. What-if сценарии

Пользователь может проверять городские сценарии.

Примеры:

- что будет, если закрыть улицу на ремонт;
- что будет, если поставить аварию;
- что будет, если снизить скорость на дороге;
- что будет, если увеличить поток машин;
- что будет, если включить random events;
- что будет, если обучать AI только на OSM-светофорах;
- что будет, если включить signals on all intersections;
- что будет, если сравнить SUMO automatic и UrbanFlow AI control.

---

## 19. Метрики

Система показывает:

- среднюю скорость;
- среднее время ожидания машин;
- congestion score;
- количество остановившихся машин;
- active vehicles;
- active pedestrians;
- throughput;
- road load;
- intersection load;
- события;
- reward;
- best reward;
- latest reward;
- saved model count;
- checkpoint path;
- training run dir.

---

## 20. Визуальная аналитика

На фронте и в notebooks используются:

- live metric charts;
- reward chart;
- wait chart;
- congestion chart;
- stopped vehicles chart;
- vehicle/pedestrian counters;
- road load;
- intersection load;
- model registry;
- AI panel;
- training panel;
- generated Jupyter notebooks;
- latest summary JSON;
- training dashboard markdown.

Визуальная аналитика должна помогать понять:

- где возникают пробки;
- как меняется waiting time;
- как AI влияет на traffic lights;
- улучшается ли reward;
- есть ли сохраненная модель;
- какие checkpoints были созданы.

---

## 21. Интерфейс

Основные панели:

### Map Selector

Выбор города и области симуляции.

Функции:

- поиск места;
- выбор центра;
- выбор размера области;
- импорт OSM;
- генерация simulation session.

### 3D City View

Главное окно с 3D-городом.

Показывает:

- дороги;
- здания;
- машины;
- пешеходов;
- общественный транспорт;
- события;
- выделение дорог;
- визуальные настройки.

### Simulation Controls

Кнопки и настройки:

- play;
- pause;
- speed;
- reset;
- mode;
- traffic light override;
- vehicle count;
- pedestrian count;
- signals on all intersections;
- apply settings.

### Editor Panel

Инструменты редактирования дорог и событий.

### Training Panel

Панель visual training.

Показывает:

- signal scope;
- curriculum;
- start vehicles;
- max vehicles;
- vehicle step;
- steps per level;
- pedestrians;
- random road events;
- start visual training;
- stop training;
- save trained model;
- export checkpoint;
- training run dir;
- checkpoint path;
- message;
- status;
- reward;
- saved models.

### Metrics Panel

Показывает ключевые метрики трафика.

### AI Panel

Показывает:

- активный AI/status;
- training summary;
- reward;
- live charts;
- состояние AI control.

### Model Registry Panel

Показывает сохраненные модели:

- label;
- path;
- scope;
- reward;
- metrics;
- delete action;
- refresh action.

---

## 22. Объяснение решений AI

Цель продукта — сделать действия AI объяснимыми.

Для каждого TLS можно показывать:

- текущую фазу;
- controlled lanes;
- количество машин;
- halted count;
- waiting time;
- occupancy;
- pressure текущей фазы;
- pressure альтернативных фаз;
- выбранную фазу;
- причину действия;
- был ли switch;
- reward effect.

Пример объяснения:

> UrbanFlow AI переключил фазу, потому что pressure альтернативной green phase выше текущей на заданный margin, а minimum green time уже прошел.

Текущая runtime-модель уже хранит action reason внутри `TlsAction`. Это можно вывести в UI как следующий слой explainability.

---

## 23. Главные фичи продукта

- выбор реального участка города;
- импорт OSM;
- генерация 3D-города;
- реальные формы дорог;
- реальные здания;
- SUMO network;
- SUMO-controlled vehicles;
- SUMO pedestrians;
- public transport support;
- реальные SUMO traffic lights;
- TraCI integration;
- редактор дорожных событий;
- аварии;
- roadworks;
- закрытие/открытие дорог;
- random events;
- режим SUMO automatic;
- режим manual fixed cycle;
- режим UrbanFlow AI;
- visual training;
- checkpoint saving;
- saved model registry;
- automatic latest model loading;
- generated notebooks;
- training history CSV/JSONL;
- live charts;
- metrics drawer;
- AI panel;
- model registry panel.

---

## 24. Почему здесь нужен AI

UrbanFlow AI решает задачу, где простые правила быстро ломаются.

Проблема:

- городская сеть динамическая;
- потоки меняются;
- перекрестки влияют друг на друга;
- аварии меняют поведение транспорта;
- ремонт меняет доступность дорог;
- локальное улучшение может ухудшить соседний перекресток;
- фиксированные тайминги не адаптируются к текущей ситуации;
- разные районы имеют разную структуру дорог.

AI нужен, чтобы принимать адаптивные решения по светофорам на основе текущего состояния SUMO-сцены.

---

## 25. Главная ценность

UrbanFlow AI помогает понять:

- где возникают пробки;
- почему возникает ожидание;
- какие перекрестки перегружены;
- какие дороги становятся bottleneck;
- как roadwork/accident влияет на район;
- как меняется traffic flow при другом управлении;
- может ли адаптивное управление светофорами улучшить ситуацию;
- какая saved model показывает лучшие метрики;
- как менялись reward и congestion во время training.

---

## 26. Для кого продукт

Потенциальные пользователи:

- урбанисты;
- транспортные инженеры;
- муниципалитеты;
- девелоперы;
- организаторы мероприятий;
- исследователи;
- студенты;
- ML-инженеры;
- разработчики симуляторов;
- геймдев-команды;
- команды, которым нужно быстро проверять городские traffic scenarios.

---

## 27. Текущее техническое состояние

Текущая версия проекта включает:

- React/Vite/TypeScript frontend;
- FastAPI backend;
- SUMO integration;
- TraCI runtime control;
- OSM import;
- SUMO scenario generation;
- dynamic vehicle spawning;
- pedestrian generation;
- public transport route/stops support;
- road editor patches;
- real SUMO traffic light states;
- UrbanFlow AI runtime controller;
- visual training jobs;
- checkpoint saving;
- model registry;
- automatic notebook generation;
- generated analytics artifacts.

Текущий AI artifact format:

```text
JSON checkpoint policy
```

Текущие неподдерживаемые или не основные runtime-форматы:

```text
ONNX
TorchScript
PyTorch neural network export
```

Они могут быть добавлены позже, если будет подключена настоящая neural policy.

---

## 28. Следующие логичные этапы развития

Следующие этапы:

- UI для объяснения решений AI по каждому светофору;
- выбор конкретной saved model из registry как active model;
- полноценный compare mode;
- автоматический benchmark нескольких режимов;
- report export;
- replay;
- heatmaps по дорогам;
- heatmaps по ожиданию;
- better pedestrian waiting metrics;
- traffic demand profiles по времени суток;
- настоящая multi-agent RL архитектура;
- graph neural network policy;
- ONNX/TorchScript export для neural policy;
- batch training/evaluation без UI;
- более подробные public transport metrics.

---

## 29. Итоговое позиционирование

**UrbanFlow AI** — это AI-powered 3D traffic simulation platform, которая превращает реальные OSM-карты в интерактивный городской симулятор на базе SUMO, позволяет редактировать дорожные сценарии, обучать и сохранять AI-контроллер светофоров, анализировать метрики и проверять, как адаптивное управление может улучшить движение в конкретном районе.

---