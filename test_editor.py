"""Швидкий тест нового 2D-редактора."""

import tkinter as tk
from ventilation_company.project3d_editor.scene.scene_graph import SceneGraph
from ventilation_company.project3d_editor.scene.entities.wall import WallEntity
from ventilation_company.project3d_editor.scene.entities.duct import DuctSegmentEntity
from ventilation_company.project3d_editor.scene.entities.fitting import DuctFittingEntity
from ventilation_company.project3d_editor.core.point import Point2D
from ventilation_company.project3d_editor.canvas2d.renderer import Canvas2DRenderer


def main():
    root = tk.Tk()
    root.title("🎨 VentCompany CAD — Тест")
    root.geometry("1200x800")

    scene = SceneGraph()

    # Додаємо демо-стіни
    scene.add_entity(WallEntity(
        name="Стіна 1", start=Point2D(0, 0), end=Point2D(5000, 0),
        thickness=200, height=3000, is_load_bearing=True, color="#555555"
    ))
    scene.add_entity(WallEntity(
        name="Стіна 2", start=Point2D(5000, 0), end=Point2D(5000, 4000),
        thickness=200, height=3000, color="#888888"
    ))
    scene.add_entity(WallEntity(
        name="Стіна 3", start=Point2D(5000, 4000), end=Point2D(0, 4000),
        thickness=200, height=3000, color="#888888"
    ))
    scene.add_entity(WallEntity(
        name="Стіна 4", start=Point2D(0, 4000), end=Point2D(0, 0),
        thickness=200, height=3000, color="#888888"
    ))

    # Додаємо повітропровід
    scene.add_entity(DuctSegmentEntity(
        name="Приплив 1", start=Point2D(500, 500), end=Point2D(4500, 500),
        width=200, height=200, duct_type="приплив", color="#0066cc"
    ))
    scene.add_entity(DuctSegmentEntity(
        name="Приплив 2", start=Point2D(4500, 500), end=Point2D(4500, 3500),
        width=200, height=200, duct_type="приплив", color="#0066cc"
    ))

    # Фасонний виріб
    scene.add_entity(DuctFittingEntity(
        name="Відвід 90°", position=Point2D(4500, 500),
        fitting_type="відвід", width_in=200, height_in=200,
        angle=90, duct_type="приплив", color="#990099"
    ))

    renderer = Canvas2DRenderer(root, scene, width=1200, height=800)

    # Підігнати під об'єкти
    root.after(100, renderer.zoom_extents)

    root.mainloop()


if __name__ == "__main__":
    main()