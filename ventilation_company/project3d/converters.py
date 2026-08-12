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
    """Конвертер IFC файлів."""

    SUPPORTED_IMPORT = [".ifc", ".ifczip", ".ifcxml"]
    SUPPORTED_EXPORT = [".ifc"]

    def can_import(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_IMPORT and IFC_AVAILABLE

    def can_export(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.SUPPORTED_EXPORT and IFC_AVAILABLE

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

    def _extract_geometry_bounds(self, element) -> Tuple[Point3D, Point3D]:
        """Отримати bounding box елемента."""
        try:
            shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), element)
            verts = shape.geometry.verts
            if verts:
                xs = verts[0::3]
                ys = verts[1::3]
                zs = verts[2::3]
                return (
                    Point3D(min(xs), min(ys), min(zs)),
                    Point3D(max(xs), max(ys), max(zs)),
                )
        except Exception:
            pass
        # Fallback: використовуємо ObjectPlacement
        try:
            placement = element.ObjectPlacement
            if placement and placement.is_a("IfcLocalPlacement"):
                coords = placement.RelativePlacement.Location.Coordinates
                if len(coords) >= 3:
                    x, y, z = coords[0], coords[1], coords[2]
                    return (Point3D(x - 500, y - 500, z), Point3D(x + 500, y + 500, z + 3000))
        except Exception:
            pass
        return (Point3D(0, 0, 0), Point3D(1000, 1000, 3000))

    def import_project(self, filepath: str) -> VentProject:
        if not IFC_AVAILABLE:
            raise ImportError(_warn_missing("ifcopenshell", "pip install ifcopenshell"))

        ifc_file = ifcopenshell.open(filepath)
        project = VentProject(
            name=os.path.splitext(os.path.basename(filepath))[0],
        )

        # ── Імпорт архітектури ──
        floors_map = {}
        for storey in ifc_file.by_type("IfcBuildingStorey"):
            level = 0
            try:
                level = float(storey.Elevation) * 1000  # м → мм
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
            bounds = self._extract_geometry_bounds(wall)
            mat = self._get_material(wall)
            thickness = 200
            try:
                thickness = float(wall.Width) * 1000 if hasattr(wall, "Width") else 200
            except Exception:
                pass

            wall_obj = Wall(
                id=wall.GlobalId,
                name=wall.Name or "Стіна",
                start=bounds[0],
                end=Point3D(bounds[1].x, bounds[1].y, bounds[0].z),
                height=bounds[1].z - bounds[0].z,
                thickness=thickness,
                material=WallMaterial.UNKNOWN,
                is_load_bearing=getattr(wall, "IsLoadBearing", True),
            )
            # Прив'язка до поверху
            storey_id = None
            try:
                for rel in wall.ContainedInStructure:
                    if rel.is_a("IfcRelContainedInSpatialStructure"):
                        storey_id = rel.RelatingStructure.GlobalId
                        break
            except Exception:
                pass
            if storey_id and storey_id in floors_map:
                floors_map[storey_id].walls.append(wall_obj)
            else:
                if not project.arch_context.floors:
                    project.arch_context.floors.append(Floor(name="Поверх 1"))
                project.arch_context.floors[0].walls.append(wall_obj)

        # Отвори
        for opening in ifc_file.by_type("IfcOpeningElement"):
            bounds = self._extract_geometry_bounds(opening)
            center = Point3D(
                (bounds[0].x + bounds[1].x) / 2,
                (bounds[0].y + bounds[1].y) / 2,
                (bounds[0].z + bounds[1].z) / 2,
            )
            width = bounds[1].x - bounds[0].x
            height = bounds[1].z - bounds[0].z
            opening_obj = Opening(
                id=opening.GlobalId,
                name=opening.Name or "Отвір",
                position=center,
                width=width,
                height=height,
            )
            if project.arch_context.floors:
                project.arch_context.floors[0].openings.append(opening_obj)

        # ── Імпорт MEP (вентиляція) ──
        # IfcDistributionElement, IfcFlowSegment, IfcFlowFitting
        ducts = []
        for elem in ifc_file.by_type("IfcFlowSegment"):
            bounds = self._extract_geometry_bounds(elem)
            start = bounds[0]
            end = bounds[1]
            length = start.distance(end)
            width = abs(bounds[1].x - bounds[0].x) or 100
            height = abs(bounds[1].z - bounds[0].z) or 100

            segment = DuctSegment(
                id=elem.GlobalId,
                start=start,
                end=end,
                width=width,
                height=height,
                length=length,
                shape=DuctShape.RECT if width != height else DuctShape.ROUND,
                material=self._get_material(elem),
            )
            ducts.append(segment)

        fittings = []
        for elem in ifc_file.by_type("IfcFlowFitting"):
            bounds = self._extract_geometry_bounds(elem)
            center = Point3D(
                (bounds[0].x + bounds[1].x) / 2,
                (bounds[0].y + bounds[1].y) / 2,
                (bounds[0].z + bounds[1].z) / 2,
            )
            fitting = Fitting(
                id=elem.GlobalId,
                position=center,
                fitting_type=elem.Name or "фасонний виріб",
                width_in=abs(bounds[1].x - bounds[0].x) or 100,
                height_in=abs(bounds[1].z - bounds[0].z) or 100,
            )
            fittings.append(fitting)

        if ducts:
            trunk = VentilationTrunk(
                name="Імпортована магістраль",
                segments=ducts,
                fittings=fittings,
            )
            system = VentilationSystem(
                name="Імпортована система",
                trunks=[trunk],
            )
            project.ventilation_systems.append(system)

        return project

    def export_project(self, project: VentProject, filepath: str) -> None:
        if not IFC_AVAILABLE:
            raise ImportError(_warn_missing("ifcopenshell", "pip install ifcopenshell"))
        # TODO: реалізувати повний IFC-експорт
        # Поки що — збереження метаданих
        meta = {
            "project_name": project.name,
            "client": project.client,
            "systems_count": len(project.ventilation_systems),
            "floors_count": len(project.arch_context.floors),
            "export_format": "IFC",
            "note": "Повний IFC-експорт буде реалізовано у наступній версії. Зараз збережено метадані.",
        }
        with open(filepath + ".meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════
# DXF/DWG Converter (AutoCAD)
# ═══════════════════════════════════════════════════════════════

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
