# SCUM: Pickup KAMAZ

Мод для SCUM (UE 4.27.2): пикап KAMAZ — свой транспорт со спавном через админ-команду,
сборкой по запчастям (двигатель, АКБ, генератор, колёса, двери, броня) и прицепом в перспективе.

Донор: **Laika** (BP_WheeledVehicle4W, 4 сиденья, 44 запчасти, полный набор механики).
Laika выбрана потому, что её посадочные анимации internally используют нейминг `Pickup_*`
(Pickup_Driver, Pickup_BL/BR/FR) — то есть анимационная база у неё уже «пикаповская».

## Дорожная карта

- **Patch 0 — Анализ и донор** — ✅ готово
  - Разбор paks SCUM (44 пака, индексы, AES-ключ).
  - Сравнение доноров: Laika (44 запчасти, 4 сиденья) vs Rager (57, 6 сидений — 2 в багажнике) vs WolfsWagen (49, 4).
  - Выбран донор: **Laika**.
  - Найден обгорелый декор `SM_Pickup_01_*_Damage` (старый пикап SCUM) — только как референс геометрии.
- **Patch 1 — Клон донора и спавн** — в работе
  - `item clone` Laika → `KAMAZ_Pickup` в проекте `.ssproj`.
  - Переименование/смещение запчастей, своя админ-команда спавна.
  - Тестовый PAK (`pakchunkNNN-KAMAZ_P.pak`).
- **Patch 2 — Blockout-меш**
  - Blender → glTF → UE 4.27 → pak. Правка багов `kamaz_scum_blockout.py`
    (wheel_z 0.78→0.61, EEVEE-фолбэк, кватернион камеры, разворот надписи, парящие стёкла, UV/LOD/коллизии/сокеты).
- **Patch 3 — Скелет под запчасти**
  - Сокеты/кости под аттачменты запчастей: Engine, Battery, Alternator, 4×Wheel, Doors, Body, Bumpers, Dashboard.
- **Patch 4 — Материалы и ливреи**
- **Patch 5 — Прицеп** (исследование механики towing — прецедентов в SCUM нет)

## Установка (клиент, одиночка/свой сервер)

1. Скопировать `pakchunkNNN-KAMAZ_P.pak` в `SCUM\SCUM\Content\Paks\`.
2. Запуск с параметрами: `-fileopenlog` и отключённым BattlEye (для одиночки).
3. Заспавнить транспорт командой (см. ниже).

## Команды

| Команда | Что делает | Статус |
|---|---|---|
| `#SpawnItem KAMAZ_Pickup` | спавн пикапа | уточняется в Patch 1 |

## Разработка

Инструменты: SCUM Modding Studio 3.6.0 CLI (`scumstudio.exe`), Blender 4.2.9, UE 4.27.2.

```bat
set SCUMSTUDIO_AES_KEY=0x0B1F4E543FB798EFC5BD861BB405BE7081CD03698EA9BA06469462A3B113CA81

scumstudio item stats "D:\SteamLibrary\steamapps\common\SCUM\SCUM\Content\Paks" BPC_Laika --json
scumstudio item clone KAMAZ.ssproj "D:\...\Paks" BPC_Laika "KAMAZ_Pickup"
scumstudio project export KAMAZ.ssproj
```

Проверка значений: `item stats` показывает каждое значение пакета — сохранённое и унаследованное
от родителя (`BP_WheeledVehicle4W`). `item set` пишет переопределение в пакет.

## Структура репозитория

```
README.md            — этот файл
kamaz_scum_blockout.py — генератор blockout-меша (Blender), правится в Patch 2
Refs/                — референсы (скриншоты желаемого вида)
Patches/             — заметки по каждому патчу
Build/               — собранные PAK (не в git, см. .gitignore)
```

## Что проверить после установки (чек-лист)

- [ ] PAK подхватился (файл на месте, игра запускается без BattlEye).
- [ ] Транспорт спавнится командой и появляется в мире.
- [ ] Посадка/выход, 4 места, руление, звук.
- [ ] Запчасти: снятие/установка колёс, двигателя, АКБ, генератора.
- [ ] Багажник-контейнер открывается.
- [ ] Урон: стёкла, двери, колёса (проколы), взрыв/пожар при уничтожении.
