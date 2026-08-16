"""Конвертери для імпорту/експорту проєктів.

Підтримує:
  • IFC (Revit, ArchiCAD, FreeCAD)
  • DWG/DXF (AutoCAD)
  • STEP (Solidworks, КОМПАС, FreeCAD)
  • FCStd (FreeCAD)
  • Власний формат .ventproj
"""

import os
import json
import tempfile
import subprocess
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod
from datetime import datetime

from ventilation_company.project3d.project_model import VentProject
from ventilation_company.project3d.vent_system import (
    Point3D, DuctSegment, DuctShape, DuctType, VentilationTrunk, VentilationSystem,
    Fitting, Equipment,
)
from ventilation_company.project3d.arch_context import (
    ArchitecturalContext, Floor, Wall, WallMaterial, Opening,
)


# ── Перевірка доступності бібліотек ──
IFC_AVAILABLE = False
try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    pass

DXF_AVAILABLE = False
try:
    import ezdxf
    DXF_AVAILABLE = True
except ImportError:
    pass


def _warn_missing(lib_name: str, pip_cmd: str):
    return f"Бібліотека {lib_name} не встановлена.\nВиконайте: {pip_cmd}"


class BaseConverter(ABC):
    """Базовий клас конвертера."""

    @abstractmethod
    def can_import(self, filepath: str) -> bool:
        pass

    @abstractmethod
    def import_project(self, filepath: str) -> VentProject:
        pass

    @abstractmethod
    def can_export(self, filepath: str) -> bool:
        pass

    @abstractmethod
    def export_project(self, project: VentProject, filepath: str) -> None:
        pass


# ═══════════════════════════════════════════════════════════════
# IFC Converter (Revit, ArchiCAD, FreeCAD)
# ═══════════════════════════════════════════════════════════════

class IFCConverter(BaseConverter):
    """Конвертер IFC файлів (покращений 2D/3D імпорт)."""

    SUPPORTED_IMPORT = [".ifc", ".ifczip", ".ifcxml"]
    SUPPORTED_EXPORT = [".ifc"]

    def can_import(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_IMPORT and IFC_AVAILABLE

    def can_export(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXPORT and IFC_AVAILABLE

    def _get_unit_scale(self, ifc_file) -> float:
        """Отримати масштаб одиниці виміру (мм в одиниці IFC)."""
        try:
            project = ifc_file.by_type("IfcProject")[0]
            units = project.UnitsInContext
            for unit in units.Units:
                if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
                    prefix = getattr(unit, "Prefix", None)
                    if prefix == "MILLI":
                        return 1.0
                    elif prefix == "CENTI":
                        return 10.0
                    elif prefix == "DECI":
                        return 100.0
                    elif prefix is None:
                        return 1000.0
        except Exception:
            pass
        return 1000.0

    def _get_property(self, element, pset_name: str, prop_name: str) -> Optional[str]:
        """Отримати значення властивості з PropertySet."""
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcPropertySet") and pset.Name == pset_name:
                        for prop in pset.HasProperties:
                            if prop.Name == prop_name and prop.is_a("IfcPropertySingleValue"):
                                val = prop.NominalValue
                                if val:
                                    return str(val.wrappedValue)
        except Exception:
            pass
        return None

    def _get_all_properties(self, element) -> dict:
        """Отримати всі властивості елемента."""
        props = {}
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcPropertySet"):
                        for prop in pset.HasProperties:
                            if prop.is_a("IfcPropertySingleValue") and prop.NominalValue:
                                props[prop.Name] = prop.NominalValue.wrappedValue
        except Exception:
            pass
        return props

    def _get_material(self, element) -> str:
        """Отримати матеріал з IFC елемента."""
        try:
            rels = element.HasAssociations
            for rel in rels:
                if rel.is_a("IfcRelAssociatesMaterial"):
                    mat = rel.RelatingMaterial
                    if mat.is_a("IfcMaterial"):
                        return mat.Name
                    elif mat.is_a("IfcMaterialLayerSetUsage"):
                        layers = mat.ForLayerSet.MaterialLayers
                        if layers:
                            return layers[0].Material.Name
        except Exception:
            pass
        return "оцинкована сталь"

    def _get_placement(self, element, scale: float = 1000.0) -> Tuple[Point3D, Optional[Tuple[float, float, float]]]:
        """Отримати розташування та напрямок елемента."""
        try:
            placement = element.ObjectPlacement
            if placement and placement.is_a("IfcLocalPlacement"):
                # Абсолютні координати
                def get_absolute_coords(pl):
                    if not pl or not pl.is_a("IfcLocalPlacement"):
                        return Point3D(0, 0, 0), (1, 0, 0)

                    rel = pl.RelativePlacement
                    loc = rel.Location
                    if loc and hasattr(loc, "Coordinates"):
                        x = float(loc.Coordinates[0]) * scale if len(loc.Coordinates) > 0 else 0
                        y = float(loc.Coordinates[1]) * scale if len(loc.Coordinates) > 1 else 0
                        z = float(loc.Coordinates[2]) * scale if len(loc.Coordinates) > 2 else 0
                        pos = Point3D(x, y, z)
                    else:
                        pos = Point3D(0, 0, 0)

                    # Напрямок
                    axis = getattr(rel, "Axis", None)
                    if axis and hasattr(axis, "DirectionRatios"):
                        dx = float(axis.DirectionRatios[0]) if len(axis.DirectionRatios) > 0 else 0
                        dy = float(axis.DirectionRatios[1]) if len(axis.DirectionRatios) > 1 else 0
                        dz = float(axis.DirectionRatios[2]) if len(axis.DirectionRatios) > 2 else 0
                        direction = (dx, dy, dz)
                    else:
                        ref = getattr(rel, "RefDirection", None)
                        if ref and hasattr(ref, "DirectionRatios"):
                            dx = float(ref.DirectionRatios[0]) if len(ref.DirectionRatios) > 0 else 1
                            dy = float(ref.DirectionRatios[1]) if len(ref.DirectionRatios) > 1 else 0
                            dz = float(ref.DirectionRatios[2]) if len(ref.DirectionRatios) > 2 else 0
                            direction = (dx, dy, dz)
                        else:
                            direction = (1, 0, 0)

                    # Рекурсивно додаємо батьківське розташування
                    parent = getattr(pl, "PlacementRelTo", None)
                    if parent:
                        parent_pos, _ = get_absolute_coords(parent)
                        pos = Point3D(pos.x + parent_pos.x, pos.y + parent_pos.y, pos.z + parent_pos.z)

                    return pos, direction

                return get_absolute_coords(placement)
        except Exception as e:
            pass
        return Point3D(0, 0, 0), (1, 0, 0)

    def _extract_duct_geometry(self, element, scale: float = 1000.0) -> Optional[Tuple[Point3D, Point3D, float, float, float, str]]:
        """
        Витягти геометрію повітропроводу: (start, end, width, height, diameter, shape).
        Повертає None, якщо не вдалося.
        """
        try:
            # Спочатку шукаємо IfcExtrudedAreaSolid в Representation
            for rep in element.Representation.Representations:
                for item in rep.Items:
                    if item.is_a("IfcExtrudedAreaSolid"):
                        profile = item.SweptArea

                        # Розміри профілю
                        width = 400
                        height = 200
                        diameter = 0
                        shape_str = "rect"

                        if profile.is_a("IfcRectangleProfileDef"):
                            width = float(profile.XDim) * scale
                            height = float(profile.YDim) * scale
                            shape_str = "rect"
                        elif profile.is_a("IfcCircleProfileDef"):
                            diameter = float(profile.Radius) * 2 * scale
                            width = diameter
                            height = diameter
                            shape_str = "round"
                        elif profile.is_a("IfcRoundedRectangleProfileDef"):
                            width = float(profile.XDim) * scale
                            height = float(profile.YDim) * scale
                            shape_str = "rect"

                        # Позиція та напрямок екструзії
                        position = item.Position
                        depth = float(item.Depth) * scale

                        # Початкова точка
                        if position and position.is_a("IfcAxis2Placement3D"):
                            loc = position.Location
                            sx = float(loc.Coordinates[0]) * scale if len(loc.Coordinates) > 0 else 0
                            sy = float(loc.Coordinates[1]) * scale if len(loc.Coordinates) > 1 else 0
                            sz = float(loc.Coordinates[2]) * scale if len(loc.Coordinates) > 2 else 0
                            start = Point3D(sx, sy, sz)

                            # Напрямок екструзії
                            axis = getattr(position, "Axis", None)
                            if axis and hasattr(axis, "DirectionRatios"):
                                dx = float(axis.DirectionRatios[0]) if len(axis.DirectionRatios) > 0 else 0
                                dy = float(axis.DirectionRatios[1]) if len(axis.DirectionRatios) > 1 else 0
                                dz = float(axis.DirectionRatios[2]) if len(axis.DirectionRatios) > 2 else 0
                            else:
                                # Беремо напрямок з extruded direction
                                ext_dir = item.ExtrudedDirection
                                dx = float(ext_dir.DirectionRatios[0])
                                dy = float(ext_dir.DirectionRatios[1])
                                dz = float(ext_dir.DirectionRatios[2])

                            # Кінцева точка = start + direction * depth
                            end = Point3D(
                                start.x + dx * depth,
                                start.y + dy * depth,
                                start.z + dz * depth,
                            )

                            return start, end, width, height, diameter, shape_str
        except Exception:
            pass

        # Fallback: використовуємо ObjectPlacement
        try:
            pos, direction = self._get_placement(element, scale)
            props = self._get_all_properties(element)

            width = 400
            height = 200
            diameter = 0
            shape_str = "rect"
            length = 1000

            # Шукаємо розміри у властивостях
            for key, val in props.items():
                key_lower = key.lower()
                if any(k in key_lower for k in ["width", "ширина", "b"]):
                    try:
                        width = float(val) * (scale / 1000.0 if float(val) < 10 else 1.0)
                    except:
                        pass
                elif any(k in key_lower for k in ["height", "висота", "h"]):
                    try:
                        height = float(val) * (scale / 1000.0 if float(val) < 10 else 1.0)
                    except:
                        pass
                elif any(k in key_lower for k in ["diameter", "діаметр", "d", "ø"]):
                    try:
                        diameter = float(val) * (scale / 1000.0 if float(val) < 10 else 1.0)
                        width = diameter
                        height = diameter
                        shape_str = "round"
                    except:
                        pass
                elif any(k in key_lower for k in ["length", "довжина", "l"]):
                    try:
                        length = float(val) * (scale / 1000.0 if float(val) < 10 else 1.0)
                    except:
                        pass

            dx, dy, dz = direction
            end = Point3D(
                pos.x + dx * length,
                pos.y + dy * length,
                pos.z + dz * length,
            )

            return pos, end, width, height, diameter, shape_str
        except Exception:
            pass

        return None

    def _get_ports(self, element, scale: float = 1000.0) -> List[Point3D]:
        """Отримати координати портів (з'єднань) елемента."""
        ports = []
        try:
            for rel in element.IsNestedBy:
                for port in rel.RelatedObjects:
                    if port.is_a("IfcDistributionPort"):
                        placement = port.ObjectPlacement
                        if placement and placement.is_a("IfcLocalPlacement"):
                            coords = placement.RelativePlacement.Location.Coordinates
                            if len(coords) >= 3:
                                ports.append(Point3D(
                                    float(coords[0]) * scale,
                                    float(coords[1]) * scale,
                                    float(coords[2]) * scale,
                                ))
        except Exception:
            pass
        return ports

    def _get_storey_for_element(self, element, floors_map: dict) -> Optional[Floor]:
        """Знайти поверх для елемента."""
        try:
            for rel in element.ContainedInStructure:
                if rel.is_a("IfcRelContainedInSpatialStructure"):
                    struct = rel.RelatingStructure
                    if struct.GlobalId in floors_map:
                        return floors_map[struct.GlobalId]
        except Exception:
            pass
        return None

    def _get_system_for_element(self, element) -> Optional[str]:
        """Знайти назву системи для елемента."""
        try:
            for rel in element.HasAssignments:
                if rel.is_a("IfcRelAssignsToGroup"):
                    group = rel.RelatingGroup
                    if group.is_a("IfcSystem"):
                        return group.Name or "Система"
        except Exception:
            pass
        return None

    def _get_element_quantity(self, element, qname: str) -> Optional[float]:
        """Отримати значення кількості (IfcElementQuantity)."""
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    qdef = rel.RelatingPropertyDefinition
                    if qdef.is_a("IfcElementQuantity") and qdef.Name == qname:
                        for q in qdef.Quantities:
                            if q.is_a("IfcQuantityLength"):
                                return float(q.LengthValue)
        except Exception:
            pass
        return None

    def import_project(self, filepath: str) -> VentProject:
        if not IFC_AVAILABLE:
            raise ImportError(_warn_missing("ifcopenshell", "pip install ifcopenshell"))

        ifc_file = ifcopenshell.open(filepath)
        scale = self._get_unit_scale(ifc_file)

        project = VentProject(
            name=os.path.splitext(os.path.basename(filepath))[0],
        )

        # ── Імпорт архітектури ──
        floors_map = {}
        for storey in ifc_file.by_type("IfcBuildingStorey"):
            level = 0
            try:
                level = float(storey.Elevation) * scale
            except Exception:
                pass
            floor = Floor(
                id=storey.GlobalId,
                name=storey.Name or f"Поверх {len(floors_map) + 1}",
                level=level,
                height=3000,
            )
            floors_map[storey.GlobalId] = floor
            project.arch_context.floors.append(floor)

        # Стіна
        for wall in ifc_file.by_type("IfcWall"):
            try:
                pos, direction = self._get_placement(wall, scale)
                # Для стіни: використовуємо bounding box або довжину
                length = 3000
                height = 3000
                thickness = 200

                # Спробуємо отримати розміри з геометрії
                for rep in wall.Representation.Representations:
                    for item in rep.Items:
                        if item.is_a("IfcExtrudedAreaSolid"):
                            profile = item.SweptArea
                            if profile.is_a("IfcRectangleProfileDef"):
                                length = float(profile.XDim) * scale
                                thickness = float(profile.YDim) * scale
                            depth = float(item.Depth) * scale
                            height = depth
                            break

                dx, dy, dz = direction
                # Проєкція на площину XY для 2D
                end = Point3D(
                    pos.x + dx * length,
                    pos.y + dy * length,
                    pos.z,
                )

                wall_obj = Wall(
                    id=wall.GlobalId,
                    name=wall.Name or "Стіна",
                    start=pos,
                    end=end,
                    height=height,
                    thickness=thickness,
                    material=WallMaterial.UNKNOWN,
                    is_load_bearing=getattr(wall, "IsLoadBearing", True),
                )

                floor = self._get_storey_for_element(wall, floors_map)
                if floor:
                    floor.walls.append(wall_obj)
                elif project.arch_context.floors:
                    project.arch_context.floors[0].walls.append(wall_obj)
            except Exception:
                pass

        # Отвори
        for opening in ifc_file.by_type("IfcOpeningElement"):
            try:
                pos, direction = self._get_placement(opening, scale)
                width = 400
                height = 300

                for rep in opening.Representation.Representations:
                    for item in rep.Items:
                        if item.is_a("IfcExtrudedAreaSolid"):
                            profile = item.SweptArea
                            if profile.is_a("IfcRectangleProfileDef"):
                                width = float(profile.XDim) * scale
                                height = float(profile.YDim) * scale
                            elif profile.is_a("IfcCircleProfileDef"):
                                width = float(profile.Radius) * 2 * scale
                                height = width
                            break

                opening_obj = Opening(
                    id=opening.GlobalId,
                    name=opening.Name or "Отвір",
                    position=pos,
                    width=width,
                    height=height,
                )
                if project.arch_context.floors:
                    project.arch_context.floors[0].openings.append(opening_obj)
            except Exception:
                pass

        # ── Імпорт MEP (вентиляція) ──
        # Групуємо сегменти за системами
        system_segments = {}
        system_fittings = {}
        system_equipment = {}

        # IfcFlowSegment — повітропроводи
        for elem in ifc_file.by_type("IfcFlowSegment"):
            try:
                geom = self._extract_duct_geometry(elem, scale)
                if geom:
                    start, end, width, height, diameter, shape_str = geom
                else:
                    # Fallback
                    pos, direction = self._get_placement(elem, scale)
                    dx, dy, dz = direction
                    length = 1000
                    end = Point3D(pos.x + dx * length, pos.y + dy * length, pos.z + dz * length)
                    start = pos
                    width, height, diameter, shape_str = 400, 200, 0, "rect"

                length = start.distance(end)

                segment = DuctSegment(
                    id=elem.GlobalId,
                    start=start,
                    end=end,
                    width=width,
                    height=height,
                    length=length,
                    shape=DuctShape.RECT if shape_str == "rect" else DuctShape.ROUND,
                    material=self._get_material(elem),
                )

                sys_name = self._get_system_for_element(elem) or "Імпортована система"
                if sys_name not in system_segments:
                    system_segments[sys_name] = []
                system_segments[sys_name].append(segment)
            except Exception:
                pass

        # IfcFlowFitting — фасонні вироби (коліна, трійники)
        for elem in ifc_file.by_type("IfcFlowFitting"):
            try:
                geom = self._extract_duct_geometry(elem, scale)
                if geom:
                    start, end, width, height, diameter, shape_str = geom
                else:
                    pos, _ = self._get_placement(elem, scale)
                    start = pos
                    end = pos
                    width, height = 400, 200

                center = Point3D(
                    (start.x + end.x) / 2,
                    (start.y + end.y) / 2,
                    (start.z + end.z) / 2,
                )

                fitting = Fitting(
                    id=elem.GlobalId,
                    position=center,
                    fitting_type=elem.Name or "фасонний виріб",
                    width_in=width,
                    height_in=height,
                    width_out=width,
                    height_out=height,
                )

                sys_name = self._get_system_for_element(elem) or "Імпортована система"
                if sys_name not in system_fittings:
                    system_fittings[sys_name] = []
                system_fittings[sys_name].append(fitting)
            except Exception:
                pass

        # IfcFlowTerminal — обладнання (вентилятори, решітки)
        for elem in ifc_file.by_type("IfcFlowTerminal"):
            try:
                pos, _ = self._get_placement(elem, scale)
                props = self._get_all_properties(elem)
                air_flow = 0
                for key, val in props.items():
                    if any(k in key.lower() for k in ["airflow", "flow", "витрата", "потік", "air"]):
                        try:
                            air_flow = float(val)
                        except:
                            pass

                width = 400
                height = 200
                length = 300

                # Спробуємо отримати розміри з геометрії
                for rep in elem.Representation.Representations:
                    for item in rep.Items:
                        if item.is_a("IfcExtrudedAreaSolid"):
                            profile = item.SweptArea
                            if profile.is_a("IfcRectangleProfileDef"):
                                width = float(profile.XDim) * scale
                                height = float(profile.YDim) * scale
                            depth = float(item.Depth) * scale
                            length = depth
                            break

                equip = Equipment(
                    id=elem.GlobalId,
                    name=elem.Name or "Обладнання",
                    position=pos,
                    width=width,
                    height=height,
                    length=length,
                    air_flow=air_flow,
                )

                sys_name = self._get_system_for_element(elem) or "Імпортована система"
                if sys_name not in system_equipment:
                    system_equipment[sys_name] = []
                system_equipment[sys_name].append(equip)
            except Exception:
                pass

        # Створюємо системи вентиляції
        all_systems = set(system_segments.keys()) | set(system_fittings.keys()) | set(system_equipment.keys())
        for sys_name in all_systems:
            segments = system_segments.get(sys_name, [])
            fittings = system_fittings.get(sys_name, [])
            equipment = system_equipment.get(sys_name, [])

            if segments or fittings or equipment:
                trunk = VentilationTrunk(
                    name=f"Магістраль {sys_name}",
                    segments=segments,
                    fittings=fittings,
                )

                # Визначаємо тип системи
                sys_type = "припливна"
                if any(k in sys_name.lower() for k in ["витяж", "витяжн", "exhaust"]):
                    sys_type = "витяжна"
                elif any(k in sys_name.lower() for k in ["приточно-витяжн", "supply-exhaust"]):
                    sys_type = "приточно-витяжна"

                system = VentilationSystem(
                    name=sys_name,
                    system_type=sys_type,
                    trunks=[trunk],
                )
                project.ventilation_systems.append(system)

        # Якщо немає вентиляційних систем, але є архітектура — це нормально
        # Користувач може додати вентиляцію вручну на основі плану

        return project

    def export_project(self, project: VentProject, filepath: str) -> None:
        """Експорт проєкту в IFC (базова реалізація)."""
        if not IFC_AVAILABLE:
            raise ImportError(_warn_missing("ifcopenshell", "pip install ifcopenshell"))

        ifc_file = ifcopenshell.file(schema="IFC4")

        ifc_project = ifc_file.create_entity(
            "IfcProject",
            GlobalId=ifcopenshell.guid.new(),
            Name=project.name,
        )

        ifc_building = ifc_file.create_entity(
            "IfcBuilding",
            GlobalId=ifcopenshell.guid.new(),
            Name="Будівля",
        )

        ifc_file.create_entity(
            "IfcRelAggregates",
            GlobalId=ifcopenshell.guid.new(),
            RelatingObject=ifc_project,
            RelatedObjects=[ifc_building],
        )

        for floor in project.arch_context.floors:
            ifc_storey = ifc_file.create_entity(
                "IfcBuildingStorey",
                GlobalId=floor.id or ifcopenshell.guid.new(),
                Name=floor.name,
                Elevation=floor.level / 1000.0,
            )
            ifc_file.create_entity(
                "IfcRelAggregates",
                GlobalId=ifcopenshell.guid.new(),
                RelatingObject=ifc_building,
                RelatedObjects=[ifc_storey],
            )

        for sys in project.ventilation_systems:
            ifc_system = ifc_file.create_entity(
                "IfcSystem",
                GlobalId=ifcopenshell.guid.new(),
                Name=sys.name,
            )

            for trunk in sys.trunks:
                for seg in trunk.segments:
                    ifc_file.create_entity(
                        "IfcFlowSegment",
                        GlobalId=seg.id or ifcopenshell.guid.new(),
                        Name=f"Сегмент {seg.width}x{seg.height}",
                    )

        ifc_file.write(filepath)
class DXFConverter(BaseConverter):
    """Конвертер DXF/DWG файлів."""

    SUPPORTED_IMPORT = [".dxf", ".dwg"]
    SUPPORTED_EXPORT = [".dxf"]

    def can_import(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_IMPORT

    def can_export(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXPORT and DXF_AVAILABLE

    def import_project(self, filepath: str) -> VentProject:
        ext = os.path.splitext(filepath)[1].lower()
        project = VentProject(
            name=os.path.splitext(os.path.basename(filepath))[0],
        )

        if ext == ".dxf" and DXF_AVAILABLE:
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()

            floor = Floor(name="Поверх 1")

            # Імпорт ліній як стін
            for entity in msp.query("LINE"):
                start = Point3D(entity.dxf.start.x, entity.dxf.start.y, entity.dxf.start.z)
                end = Point3D(entity.dxf.end.x, entity.dxf.end.y, entity.dxf.end.z)
                wall = Wall(
                    name="Стіна (з DXF)",
                    start=start,
                    end=end,
                    height=3000,
                    thickness=200,
                )
                floor.walls.append(wall)

            # Імпорт LWPOLYLINE як стін/перегородок
            for entity in msp.query("LWPOLYLINE"):
                points = list(entity.vertices_in_wcs())
                for i in range(len(points) - 1):
                    p1 = Point3D(points[i][0], points[i][1], 0)
                    p2 = Point3D(points[i + 1][0], points[i + 1][1], 0)
                    wall = Wall(
                        name="Перегородка (з DXF)",
                        start=p1,
                        end=p2,
                        height=3000,
                        thickness=150,
                    )
                    floor.walls.append(wall)

            # Імпорт колів як отвори/вентиляційні елементи
            for entity in msp.query("CIRCLE"):
                center = Point3D(entity.dxf.center.x, entity.dxf.center.y, entity.dxf.center.z)
                diameter = entity.dxf.radius * 2
                # Якщо діаметр > 100 мм — це може бути повітропровід
                if diameter > 100:
                    opening = Opening(
                        name=f"Отвір Ø{diameter:.0f}",
                        position=center,
                        width=diameter,
                        height=diameter,
                        shape="круглий",
                        diameter=diameter,
                    )
                    floor.openings.append(opening)

            project.arch_context.floors.append(floor)
            project.add_drawing(filepath, floor="Поверх 1", drawing_type="план")

        elif ext == ".dwg":
            # DWG — бінарний формат AutoCAD. ezdxf не підтримує читання DWG.
            # Використовуємо ODA File Converter або Teigha як зовнішній інструмент.
            project.notes = "DWG файл додано як довідковий. Для імпорту геометрії конвертуйте у DXF."
            project.add_drawing(filepath, floor="Поверх 1", drawing_type="план")

        return project

    def export_project(self, project: VentProject, filepath: str) -> None:
        if not DXF_AVAILABLE:
            raise ImportError(_warn_missing("ezdxf", "pip install ezdxf"))

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Експорт стін
        for floor in project.arch_context.floors:
            for wall in floor.walls:
                msp.add_line(
                    start=(wall.start.x, wall.start.y, wall.start.z),
                    end=(wall.end.x, wall.end.y, wall.end.z),
                )

        # Експорт повітропроводів
        for system in project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    msp.add_line(
                        start=(seg.start.x, seg.start.y, seg.start.z),
                        end=(seg.end.x, seg.end.y, seg.end.z),
                    )

        # Експорт обладнання як колів
        for system in project.ventilation_systems:
            for trunk in system.trunks:
                for eq in trunk.equipment:
                    msp.add_circle(
                        center=(eq.position.x, eq.position.y),
                        radius=max(eq.width, eq.height) / 2,
                    )

        doc.saveas(filepath)


# ═══════════════════════════════════════════════════════════════
# STEP Converter (Solidworks, КОМПАС, FreeCAD)
# ═══════════════════════════════════════════════════════════════

class STEPConverter(BaseConverter):
    """Конвертер STEP файлів (AP203/AP214/AP242)."""

    SUPPORTED_IMPORT = [".step", ".stp"]
    SUPPORTED_EXPORT = [".step", ".stp"]

    def can_import(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_IMPORT

    def can_export(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXPORT

    def _parse_step_simple(self, filepath: str) -> List[Dict[str, Any]]:
        """Спрощений парсер STEP — витягує геометрію CARTESIAN_POINT."""
        entities = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Шукаємо CARTESIAN_POINT
        import re
        points = []
        for match in re.finditer(r"CARTESIAN_POINT\s*'[^']*'\s*\(([^)]+)\)", content):
            coords_str = match.group(1)
            try:
                coords = [float(x.strip()) for x in coords_str.split(",")]
                if len(coords) >= 3:
                    points.append(Point3D(coords[0], coords[1], coords[2]))
            except ValueError:
                continue

        # Групуємо точки у лінії (по 2)
        for i in range(0, len(points) - 1, 2):
            entities.append({
                "type": "line",
                "start": points[i],
                "end": points[i + 1],
            })

        return entities

    def import_project(self, filepath: str) -> VentProject:
        project = VentProject(
            name=os.path.splitext(os.path.basename(filepath))[0],
        )

        entities = self._parse_step_simple(filepath)
        if entities:
            floor = Floor(name="Поверх 1")
            for ent in entities:
                if ent["type"] == "line":
                    wall = Wall(
                        name="Елемент (з STEP)",
                        start=ent["start"],
                        end=ent["end"],
                        height=3000,
                        thickness=200,
                    )
                    floor.walls.append(wall)
            project.arch_context.floors.append(floor)

        project.notes = f"Імпортовано з STEP: {len(entities)} елементів. Для повного імпорту рекомендується використовувати FreeCAD."
        return project

    def export_project(self, project: VentProject, filepath: str) -> None:
        """Експорт у STEP через FreeCAD CLI (якщо доступний)."""
        from ventilation_company.freecad_models import FREECAD_AVAILABLE, FREECAD_CMD

        if FREECAD_AVAILABLE and FREECAD_CMD:
            # Створюємо тимчасовий Python-скрипт для FreeCAD
            script = self._build_freecad_export_script(project, filepath)
            script_path = os.path.join(tempfile.gettempdir(), "vent_step_export.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)

            result = subprocess.run(
                [FREECAD_CMD, script_path],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Помилка FreeCAD STEP-експорту: {result.stderr}")
        else:
            # Спрощений STEP-експорт (ASCII)
            self._export_simple_step(project, filepath)

    def _build_freecad_export_script(self, project: VentProject, filepath: str) -> str:
        lines = [
            "import FreeCAD, Part, Import",
            "doc = FreeCAD.newDocument('VentProject')",
        ]
        for system in project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    lines.append(
                        f"l = Part.makeLine(FreeCAD.Vector({seg.start.x},{seg.start.y},{seg.start.z}), "
                        f"FreeCAD.Vector({seg.end.x},{seg.end.y},{seg.end.z}))"
                    )
                    lines.append("doc.addObject('Part::Feature', 'Duct').Shape = l")
        lines.append(f"Import.export(doc.Objects, '{filepath}')")
        lines.append("doc.close()")
        return "\n".join(lines)

    def _export_simple_step(self, project: VentProject, filepath: str) -> None:
        """Спрощений STEP-експорт (без FreeCAD)."""
        lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION((''), '2;1');",
            f"FILE_NAME('{os.path.basename(filepath)}', '{datetime.now().isoformat()}', ('VentCompany'), (''), '', '', '');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 3 1 1 }'));",
            "ENDSEC;",
            "DATA;",
        ]
        entity_id = 10
        for system in project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    lines.append(f"#{entity_id}=CARTESIAN_POINT('',({seg.start.x},{seg.start.y},{seg.start.z}));")
                    entity_id += 1
                    lines.append(f"#{entity_id}=CARTESIAN_POINT('',({seg.end.x},{seg.end.y},{seg.end.z}));")
                    entity_id += 1
        lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


# ═══════════════════════════════════════════════════════════════
# FreeCAD Converter
# ═══════════════════════════════════════════════════════════════

class FreeCADConverter(BaseConverter):
    """Конвертер FreeCAD (.FCStd) файлів."""

    SUPPORTED_IMPORT = [".fcstd", ".FCStd"]
    SUPPORTED_EXPORT = [".fcstd", ".FCStd"]

    def can_import(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_IMPORT

    def can_export(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXPORT

    def import_project(self, filepath: str) -> VentProject:
        from ventilation_company.freecad_models import FREECAD_AVAILABLE, FREECAD_CMD

        project = VentProject(
            name=os.path.splitext(os.path.basename(filepath))[0],
        )

        if FREECAD_AVAILABLE and FREECAD_CMD:
            # Використовуємо FreeCAD CLI для імпорту
            script = f"""
import FreeCAD
import json
doc = FreeCAD.openDocument("{filepath}")
result = {{"objects": []}}
for obj in doc.Objects:
    if hasattr(obj, "Shape"):
        bb = obj.Shape.BoundBox
        result["objects"].append({{
            "name": obj.Name,
            "label": obj.Label,
            "x_min": bb.XMin, "y_min": bb.YMin, "z_min": bb.ZMin,
            "x_max": bb.XMax, "y_max": bb.YMax, "z_max": bb.ZMax,
        }})
with open("{tempfile.gettempdir()}/vent_fc_import.json", "w", encoding="utf-8") as f:
    json.dump(result, f)
doc.close()
"""
            script_path = os.path.join(tempfile.gettempdir(), "vent_fc_import.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)

            result = subprocess.run(
                [FREECAD_CMD, script_path],
                capture_output=True, text=True, timeout=120,
            )

            json_path = os.path.join(tempfile.gettempdir(), "vent_fc_import.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                floor = Floor(name="Поверх 1")
                for obj in data.get("objects", []):
                    wall = Wall(
                        name=obj.get("label", obj.get("name", "Елемент")),
                        start=Point3D(obj["x_min"], obj["y_min"], obj["z_min"]),
                        end=Point3D(obj["x_max"], obj["y_max"], obj["z_min"]),
                        height=obj["z_max"] - obj["z_min"],
                        thickness=200,
                    )
                    floor.walls.append(wall)
                project.arch_context.floors.append(floor)
        else:
            project.notes = "FreeCAD не знайдено. Файл додано як довідковий."

        return project

    def export_project(self, project: VentProject, filepath: str) -> None:
        from ventilation_company.freecad_models import FREECAD_AVAILABLE, FREECAD_CMD

        if not FREECAD_AVAILABLE or not FREECAD_CMD:
            raise RuntimeError("FreeCAD не знайдено. Встановіть FreeCAD для експорту у FCStd.")

        script = self._build_freecad_export_script(project, filepath)
        script_path = os.path.join(tempfile.gettempdir(), "vent_fc_export.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        result = subprocess.run(
            [FREECAD_CMD, script_path],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Помилка FreeCAD-експорту: {result.stderr}")

    def _build_freecad_export_script(self, project: VentProject, filepath: str) -> str:
        lines = [
            "import FreeCAD, Part",
            "doc = FreeCAD.newDocument('VentProject')",
        ]
        idx = 0
        for system in project.ventilation_systems:
            for trunk in system.trunks:
                for seg in trunk.segments:
                    lines.append(
                        f"l{idx} = Part.makeLine(FreeCAD.Vector({seg.start.x},{seg.start.y},{seg.start.z}), "
                        f"FreeCAD.Vector({seg.end.x},{seg.end.y},{seg.end.z}))"
                    )
                    lines.append(f"doc.addObject('Part::Feature', 'Duct_{idx}').Shape = l{idx}")
                    idx += 1
                for eq in trunk.equipment:
                    lines.append(
                        f"box = Part.makeBox({eq.length},{eq.width},{eq.height}, "
                        f"FreeCAD.Vector({eq.position.x},{eq.position.y},{eq.position.z}))"
                    )
                    lines.append(f"doc.addObject('Part::Feature', 'Eq_{eq.name}').Shape = box")
        lines.append(f"doc.saveAs('{filepath}')")
        lines.append("doc.close()")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Project Converter Hub
# ═══════════════════════════════════════════════════════════════

class ProjectConverter:
    """Головний хаб для конвертації проєктів."""

    CONVERTERS = [
        IFCConverter(),
        DXFConverter(),
        STEPConverter(),
        FreeCADConverter(),
    ]

    @classmethod
    def import_file(cls, filepath: str) -> VentProject:
        """Імпортувати файл у VentProject."""
        ext = os.path.splitext(filepath)[1].lower()

        for converter in cls.CONVERTERS:
            if converter.can_import(filepath):
                return converter.import_project(filepath)

        # Якщо ніхто не підтримує — додаємо як довідковий файл
        project = VentProject(name=os.path.splitext(os.path.basename(filepath))[0])
        project.add_drawing(filepath, drawing_type="довідковий")
        project.notes = f"Формат {ext} не підтримується для автоматичного імпорту геометрії. Файл додано як довідковий."
        return project

    @classmethod
    def export_file(cls, project: VentProject, filepath: str) -> None:
        """Експортувати VentProject у файл."""
        ext = os.path.splitext(filepath)[1].lower()

        for converter in cls.CONVERTERS:
            if converter.can_export(filepath):
                converter.export_project(project, filepath)
                return

        # Якщо ніхто не підтримує — зберігаємо у .ventproj
        if ext != ".ventproj":
            filepath = os.path.splitext(filepath)[0] + ".ventproj"
        project.save(filepath)

    @classmethod
    def get_supported_import_formats(cls) -> List[Tuple[str, str]]:
        """Повертає список підтримуваних форматів імпорту."""
        formats = []
        if IFC_AVAILABLE:
            formats.append(("IFC (Revit, ArchiCAD)", "*.ifc *.ifczip"))
        if DXF_AVAILABLE:
            formats.append(("DXF (AutoCAD)", "*.dxf"))
        formats.append(("DWG (AutoCAD)", "*.dwg"))
        formats.append(("STEP (Solidworks)", "*.step *.stp"))
        formats.append(("FreeCAD", "*.fcstd *.FCStd"))
        formats.append(("VentProject", "*.ventproj"))
        return formats

    @classmethod
    def get_supported_export_formats(cls) -> List[Tuple[str, str]]:
        """Повертає список підтримуваних форматів експорту."""
        formats = []
        if IFC_AVAILABLE:
            formats.append(("IFC (Revit)", "*.ifc"))
        if DXF_AVAILABLE:
            formats.append(("DXF (AutoCAD)", "*.dxf"))
        formats.append(("STEP (Solidworks)", "*.step *.stp"))
        formats.append(("FreeCAD", "*.fcstd"))
        formats.append(("VentProject", "*.ventproj"))
        return formats
