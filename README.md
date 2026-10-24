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
- **Patch 1 — Клон донора и спавн** — ✅ готово ([Release v0.1.0-patch1](https://github.com/bLemann/SCUM-Pickup-KAMAZ/releases/tag/v0.1.0-patch1))
  - `item clone` Laika → `BPC_KAMAZ_Pickup`: 122 пакета (все запчасти, меши, материалы, кривые, 4 пресета спавна).
  - Команда спавна: `#SpawnVehicle BPC_KAMAZ_Pickup`.
  - Тестовый PAK собран и провалидирован (123 пакета, 0 проблем), выложен в Release.
- **Patch 2 — Blockout-меш**
  - Blender → glTF → UE 4.27 → pak. Правка багов `kamaz_scum_blockout.py`
    (wheel_z 0.78→0.61, EEVEE-фолбэк, кватернион камеры, разворот надписи, парящие стёкла, UV/LOD/коллизии/сокеты).
- **Patch 3 — Скелет под запчасти**
  - Сокеты/кости под аттачменты запчастей: Engine, Battery, Alternator, 4×Wheel, Doors, Body, Bumpers, Dashboard.
- **Patch 4 — Материалы и ливреи**
- **Patch 5 — Прицеп** (исследование механики towing — прецедентов в SCUM нет)

## Установка (клиент, одиночка/свой сервер)

Готовый PAK — в [Releases](https://github.com/bLemann/SCUM-Pickup-KAMAZ/releases).

1. Скопировать `pakchunk900-KAMAZ_P.pak` и `pakchunk900-KAMAZ_P.sig` в `SCUM\SCUM\Content\Paks\~mods\`.
2. Запуск с параметрами: `-fileopenlog` и отключённым BattlEye (для одиночки).
3. Заспавнить транспорт командой (см. ниже).

## Команды

| Команда | Что делает | Статус |
|---|---|---|
| `#SpawnVehicle BPC_KAMAZ_Pickup` | спавн пикапа (4 пресета комплектации) | проверить в игре |

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
KAMAZ.ssproj/        — проект SCUM Modding Studio (manifest, journal, notes)
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
