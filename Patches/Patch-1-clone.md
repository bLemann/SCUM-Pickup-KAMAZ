# Patch 1 — Клон донора и спавн

## Что сделано

1. Создан проект `KAMAZ.ssproj` (`scumstudio project new`, сборка игры 25804202, источник — клиентские Paks).
2. Клонирован донор: `item clone KAMAZ.ssproj <Paks> BPC_Laika KAMAZ_Pickup` — **122 пакета**:
   - сам предмет `BPC_KAMAZ_Pickup` + энтити-спавнер `KAMAZ_Pickup_ES`;
   - 4 пресета ручного спавна (`ManualSpawn`: базовый, `_Full`, `_MinimalFunctional`, `_WheelsOnly`);
   - анимации `ABP_KAMAZ_Pickup(+_Dashboard)`, input `IM_KAMAZ_Pickup`;
   - кривые: крутящий момент, руление, расход топлива, заряд генератора;
   - все 44 запчасти: Chassis, Body×4, Doors, DoorHood/DoorTrunk, Bumpers, Dashboard, Seats×3, Wheels×4,
     Engine + Alternator + Battery, Gearbox, Headlights, Brakelights, Radio, RoofRack, броня Light/Heavy;
   - контейнер багажника `KAMAZ_Pickup_Item_Container(+_ES)`, шины `KAMAZ_Pickup_Tires(+_Flat)`;
   - меши и материалы `SK_/SM_/MI_KAMAZ_Pickup_*` (пока геометрия Laika);
   - 6 MountSlots (4 сиденья + 2 толкания), 4 WAP (стрельба из окон), кривые обзора.
3. Сборка: `project export -o Build --client-only` →
   `Build\KAMAZ\Client\pakchunk900-KAMAZ_P.pak` (247 записей, 91,5 МБ, pak v11 UE 4.27) + `.sig`.
   Валидатор: **123 пакета, 0 проблем**. AssetRegistry: 98 записей.
4. Установка в игру: скопирован в `SCUM\SCUM\Content\Paks\~mods\`.
5. Релиз: [v0.1.0-patch1](https://github.com/bLemann/SCUM-Pickup-KAMAZ/releases/tag/v0.1.0-patch1) — PAK + sig + чек-лист проверки.

## Команда спавна

```
#SpawnVehicle BPC_KAMAZ_Pickup
```

Выдаётся самим клоном (пресеты ручного спавна перезаписаны под новое имя).

## Как проверить

См. чек-лист в Release notes / README. Кратко: спавн, 4 места, запчасти, багажник, проколы, взрыв.

## Известные ограничения

- Геометрия/звук/характеристики — Laika. Свой меш — Patch 2 (правки `kamaz_scum_blockout.py`).
- BattlEye не даст моду работать на чужих серверах.

## Артефакты

- `KAMAZ.ssproj/journal.jsonl` — журнал правок (воспроизводимо: `project status`, `history`, `undo/redo`).
- `Build/KAMAZ/Client/export-report.md` — отчёт экспорта.
