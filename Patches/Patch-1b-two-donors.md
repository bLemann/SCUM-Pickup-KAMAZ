# Patch 1b — Два донора: Rager (основной) + Laika

## Почему изменён выбор

Игрок (владелец проекта) указал, что **Rager в игре — пикап**. Проверка по пакам это подтверждает:

- Меши Rager лежат в `ConZ_Files/Models/Vehicles2/Pickup/Meshes/` — то есть Rager построен
  на модели старого пикапа `Pickup_01` (та самая, чьи обгорелые декорации мы нашли в Patch 0).
- У Rager 6 MountSlot_Seat: 4 в кабине + **Seat_TrunkLeft/Seat_TrunkRight — сиденья в кузове**.
- 57 аттачментов (больше всех машин), бронированные колёса как отдельные запчасти.

Изначальный выбор Laika (Patch 0) сделан по анимационному признаку (`Pickup_*` кривые),
но по геометрии Rager ближе к целевому KAMAZ-пикапу.

## Что сделано

1. `project undo` — откат Laika-клона из Patch 1 (он остался в истории журнала).
2. `item clone BPC_Rager → KAMAZ_Pickup` — **BPC_KAMAZ_Pickup**, основной вариант.
3. `item clone BPC_Laika → KAMAZ_Pickup_Laika` — **BPC_KAMAZ_Pickup_Laika**, вариант для сравнения.
4. `project export` → `pakchunk900-KAMAZ_P.pak`: **555 записей, 164 МБ**, валидатор
   **277 пакетов, 0 проблем**, 220 записей AssetRegistry, 8 пресетов спавна (4+4).
5. PAK установлен в `~mods` игры.
6. Релиз: [v0.1.1-patch1](https://github.com/bLemann/SCUM-Pickup-KAMAZ/releases/tag/v0.1.1-patch1).

## Команды

```
#SpawnVehicle BPC_KAMAZ_Pickup          # вариант на Rager (пикап)
#SpawnVehicle BPC_KAMAZ_Pickup_Laika    # вариант на Laika (седан)
```

## Что проверить

- Спавнятся ли оба варианта, чем отличаются в живой игре (посадка в кузов на Rager-варианте!).
- Какой силуэт ближе к референсам KAMAZ из `Refs/` — это решит, чьи меши заменяем в Патче 2/3.

## Влияние на Патч 2

Меши Rager живут в `Models/Vehicles2/Pickup/` — при замене геометрии ориентироваться на
структуру `SK_Rager_*`/`SM_Rager_*` (имена уже переклонированы в `SK_KAMAZ_Pickup_*`).
Blockout-меш из `kamaz_scum_blockout.py` не меняется — он доноро-независимый.
