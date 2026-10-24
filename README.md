# SCUM: Pickup KAMAZ

Мод для SCUM (UE 4.27.2): пикап KAMAZ — свой транспорт со спавном через админ-команду,
сборкой по запчастям (двигатель, АКБ, генератор, колёса, двери, броня) и прицепом в перспективе.

Доноры (два варианта в одном PAK):

- **Rager → `BPC_KAMAZ_Pickup`** — основной. Rager в игре — пикап (его меши лежат в
  `Models/Vehicles2/Pickup/`, 2 сиденья в кузове, 57 запчастей — больше всех, бронированные колёса).
- **Laika → `BPC_KAMAZ_Pickup_Laika`** — вариант для сравнения (4-дверка, посадочные анимации
  с неймингом `Pickup_*`, 44 запчасти).

Спавн в игре: `#SpawnVehicle BPC_KAMAZ_Pickup` и `#SpawnVehicle BPC_KAMAZ_Pickup_Laika`.

## Дорожная карта

- **Patch 0 — Анализ и донор** — ✅ готово
  - Разбор paks SCUM (44 пака, индексы, AES-ключ).
  - Сравнение доноров: Laika (44 запчасти, 4 сиденья) vs Rager (57, 6 сидений — 2 в багажнике) vs WolfsWagen (49, 4).
  - Первый выбор: Laika. Исправлено в Patch 1b: **основной донор — Rager** (в игре это пикап,
    меши в `Models/Vehicles2/Pickup/`), Laika оставлена вторым вариантом.
  - Найден обгорелый декор `SM_Pickup_01_*_Damage` (старый пикап SCUM) — только как референс геометрии.
- **Patch 1 — Клон донора и спавн** — ✅ готово ([Release v0.1.1-patch1](https://github.com/bLemann/SCUM-Pickup-KAMAZ/releases/tag/v0.1.1-patch1), два донора)
  - `item clone`: Rager → `BPC_KAMAZ_Pickup` (122→136 пакетов) + Laika → `BPC_KAMAZ_Pickup_Laika`.
  - Команды спавна: `#SpawnVehicle BPC_KAMAZ_Pickup`, `#SpawnVehicle BPC_KAMAZ_Pickup_Laika`.
  - Тестовый PAK собран и провалидирован (277 пакетов, 0 проблем), выложен в Release.
- **Patch 2 — Blockout-меш** — 🔶 в работе
  - Blender → glTF → UE 4.27 → pak. Правка багов `kamaz_scum_blockout.py`
    (wheel_z 0.78→0.61, EEVEE-фолбэк, кватернион камеры, разворот надписи, парящие стёкла, UV/LOD/коллизии/сокеты).
  - Готово: блокаут сгенерирован и отрендерен — LOD0 (2456 verts / 3816 tris) + LOD1 0.5 + LOD2 0.25,
    3 UCX-бокса коллизий, smart UV 66°; экспорт FBX + glTF + UV-развёртка;
    превью (UCX/LOD скрыты из рендера): [Docs/renders/](Docs/renders) — front 3/4, side, rear 3/4.
  - Пропорции приведены к референсу Rager ([Refs/Rager_reference.png](Refs/Rager_reference.png)):
    двойная кабина на 4 двери, длинный кузов с чёрной крышкой (tonneau), лифтованная посадка,
    большие грязевые колёса, чёрный обвес (арки, пороги, бампер с защитой), рейлинги с антенной,
    спорт-бар за кабиной, LED-оптика с голубыми ХОГ, красные буксировочные проушины.
    Кузов — светло-серый под камуфляж (окраска/ливрея — Patch 4).
  - Далее: подмена меша донора на свой (путь импорта в PAK — pkg/modshare/UE 4.27, исследуется).
- **Patch 3 — Скелет под запчасти**
  - Сокеты/кости под аттачменты запчастей: Engine, Battery, Alternator, 4×Wheel, Doors, Body, Bumpers, Dashboard.
- **Patch 4 — Материалы и ливреи**
- **Patch 5 — Прицеп** (исследование механики towing — прецедентов в SCUM нет)

## Установка (клиент, одиночка/свой сервер)

Готовый PAK — в [Releases](https://github.com/bLemann/SCUM-Pickup-KAMAZ/releases).

1. Скопировать `pakchunk900-KAMAZ_P.pak` в `SCUM\SCUM\Content\Paks\~mods\`. **Файл `.sig` не нужен — удалите его, если ставили:** `project export` подкладывает рядом с паком копию чужой стоковой сигнатуры (`pakchunk44`), с ней игра показывает «Serialization Error: Corrupt data found» и не запускается.
2. Запуск с параметрами: `-fileopenlog` и отключённым BattlEye (для одиночки).
3. Заспавнить транспорт командой (см. ниже).

## Команды

| Команда | Что делает | Статус |
|---|---|---|
| `#SpawnVehicle BPC_KAMAZ_Pickup` | спавн пикапа (вариант на базе Rager) | проверить в игре |
| `#SpawnVehicle BPC_KAMAZ_Pickup_Laika` | спавн пикапа (вариант на базе Laika) | проверить в игре |

## Разработка

Инструменты: SCUM Modding Studio 3.6.0 CLI (`scumstudio.exe`), Blender 4.2.9, UE 4.27.2.

**Patch 3 (исследование):** свой меш для машины делается без GUI студии — UE 4.27 headless
(`UE4Editor-Cmd.exe`: pythonscript-импорт FBX → cook WindowsNoEditor), затем `scumstudio pak pack`
из staging экспорта с подменой клон-меша cooked-файлом под тем же именем. Пайплайн проверен
end-to-end: тест-пак `pakchunk901-KAMAZTEST_P.pak` заменяет переднее левое колесо KAMAZ'а целым
блокаут-пикапом. Подробности и ограничения — `Patches/Patch-3-mesh-pipeline.md`; скрипт импорта —
`tools/ue_import_kamaz.py`.

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
tools/               — вспомогательные скрипты (UE-импорт для Patch 3)
Refs/                — референсы (скриншоты желаемого вида)
Patches/             — заметки по каждому патчу
Docs/renders/        — превью blockout-меша (Patch 2)
Build/               — собранные PAK (не в git, см. .gitignore)
```

## Что проверить после установки (чек-лист)

- [ ] PAK подхватился (файл на месте, игра запускается без BattlEye).
- [ ] Транспорт спавнится командой и появляется в мире.
- [ ] Посадка/выход, 4 места, руление, звук.
- [ ] Запчасти: снятие/установка колёс, двигателя, АКБ, генератора.
- [ ] Багажник-контейнер открывается.
- [ ] Урон: стёкла, двери, колёса (проколы), взрыв/пожар при уничтожении.
