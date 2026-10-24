# Patch 3 — свой меш: проверенный headless-пайплайн

Статус: пайплайн доказан end-to-end; тест в игре — за владельцем.

## Что выяснено (исследование студии)

- Импорта мешей в scumstudio нет ни в одной команде (`pkg/asset/item/level/mcp/pak/pkg/project/render/modshare`).
- Свап модели части в игре работает через `MeshSetup.Mesh` у blueprint'а части: игра рисует модель
  на сокете/костной точке части, с пивотом самой модели (CHANGELOG 3.6.0, кейс «ZIL-колёса на Rager»).
  Донором может быть StaticMesh (проп-колесо `ZIL131/Props/SM_Wheel_01`). Но записать этот ключ можно
  только из GUI студии (вкладка Vehicles → «Другая модель…») или через её MCP-сервер — в CLI `item set`
  части машин не входят (только item-семейство).
- `item clone` клонирует ВСЕ пакеты донора (машина + ES + пресеты + части + меши + материалы) и
  переписывает ссылки внутри клонированных файлов на новые имена: `SK_Rager → SK_KAMAZ_Pickup`,
  `SM_Rager_Wheel_FrontLeft → SM_KAMAZ_Pickup_Wheel_FrontLeft` и т.д. (см. `KAMAZ.ssproj/journal.jsonl`).
  Следствие: клонированный blueprint части уже ссылается на пакет-клон меша → **если подсунуть в пак
  свой cooked-меш под именем клона, игра нарисует его без каких-либо правок свойств**.
- `project export` пишет staging в `<out>/<Name>/Client/.work/staging/SCUM/Content/...` — это ВЫХОД,
  не вход (перезаписывается при каждом экспорте). Ключ к сборке — `scumstudio pak pack`.

## Пайплайн (проверен)

1. **Blender** — блокаут → FBX (`kamaz_scum_blockout.py`).
2. **UE 4.27.2 headless** (E:\Games\UE_4.27, полный редактор; бинарник называется `UE4Editor-Cmd.exe`,
   UE5-нейминг тут не работает):
   - проект: `D:\SteamLibrary\KAMAZ_UE\KAMAZ_UE.uproject`, `"EngineAssociation": "E:\\Games\\UE_4.27"`
     (в реестре движок не зарегистрирован — абсолютный путь в .uproject решает это);
   - DDC: `Set-Item env:UE-LocalDataCachePath D:\SteamLibrary\KAMAZ_UE\DDC`;
   - импорт: `-run=pythonscript -script=import_kamaz.py` (FBXImportUI, combine_meshes,
     import_materials=False) — ассет создаётся сразу под именем-клоном:
     `/Game/ConZ_Files/Models/Vehicles2/Pickup/Meshes/SM_KAMAZ_Pickup_Wheel_FrontLeft`
     (внутреннее имя пакета обязано совпадать с именем файла — переименовывать cooked-файлы нельзя);
   - cook: `-run=cook -targetplatform=WindowsNoEditor -unversioned -iterate -nullrhi`.
3. **Сборка пака**: скопировать staging экспорта → перезаписать клон-меш cooked-файлами
   (.uasset/.uexp) → `scumstudio pak pack <staging> -o pakchunk901-KAMAZTEST_P.pak`
   (без `--compression` — студия не читает собственные zlib-записи; игра стоковые паки читает,
   но лишнюю переменную в тест не вводим; `.sig` рядом не класть — см. Patch 1).
4. **Проверка**: `scumstudio render mesh <pak> /Game/.../SM_KAMAZ_Pickup_Wheel_FrontLeft` — рендерит
   содержимое пака тем же загрузчиком, что у игры.

## Тест-пак 901

- `pakchunk901-KAMAZTEST_P.pak` = копия 900 (клон машины) + заменённый
  `SM_KAMAZ_Pickup_Wheel_FrontLeft` = целый блокаут-пикап вместо переднего левого колеса.
- Дефолтный спавн-пресет (`KAMAZ_PickupManualSpawnPreset`) включает: Body F/L/R/T, Brakelights,
  BrakeLight_Top, Bumpers, Chassis, Dashboard, все двери, DoorHood, DoorTrunk, Engine, Alternator,
  Battery, Gearbox, Headlights, Radio, 3 сиденья, **все 4 колеса**. RoofRack в базовом пресете нет.
- Колесо выбрано целью потому, что это StaticMesh-часть (класс совпадает, скелет не нужен) и оно
  есть в любом пресете (вплоть до WheelsOnly).

## Известные ограничения (следующие шаги)

- Материалы: все слоты замаплены на `/Engine/EngineMaterials/WorldGridMaterial` (серая сетка).
  Дальше — свои простые материалы в кули-проекте либо перепайка слотов на игровые `MI_KAMAZ_Pickup_*`.
- FBX сейчас тащит LOD1/2 и UCX (37 175 трис вместо 3 816 LOD0) — `combine_meshes` слепил всё.
  Для чистого экспорта: один LOD, без UCX-объектов в FBX.
- Кузов — SkeletalMesh (`SK_KAMAZ_Pickup*`): подмена класса не прокатывает, нужен либо cook
  SkeletalMesh на костях донорского скелета, либо `MeshSetup.Mesh` (GUI/MCP студии).
- Скрипт импорта: `tools/ue_import_kamaz.py` (копия `D:\SteamLibrary\KAMAZ_UE\import_kamaz.py`).
