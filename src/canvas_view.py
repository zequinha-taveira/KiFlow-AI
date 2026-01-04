from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QTextEdit, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QColor, QPen, QBrush, QPainter

class CanvasView(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1e293b; border-radius: 12px; background: #1e293b; top: -1px; }
            QTabBar::tab { 
                background: #0f172a; 
                color: #64748b; 
                padding: 12px 24px; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px; 
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 0.5px;
                margin-right: 4px;
            }
            QTabBar::tab:selected { 
                background: #1e293b; 
                color: #38bdf8; 
                border-bottom: 3px solid #38bdf8; 
            }
            QTabBar::tab:hover:!selected { background: #1e293b; color: #94a3b8; }
        """)

        # Tab 1: Architecture
        self.arch_view = QTextEdit()
        self.arch_view.setReadOnly(True)
        self.arch_view.setStyleSheet("background-color: #020617; color: #94a3b8; font-family: 'Fira Code', 'Consolas'; border: none; padding: 20px;")
        self.tabs.addTab(self.arch_view, "STRUCTURE")

        # Tab 2: PCB Preview
        self.pcb_scene = QGraphicsScene()
        self.pcb_view = QGraphicsView(self.pcb_scene)
        self.pcb_view.setRenderHint(QPainter.Antialiasing) 
        self.pcb_view.setStyleSheet("background-color: #020617; border: none;") 
        self.tabs.addTab(self.pcb_view, "PCB LAYOUT")

        # Tab 3: BOM
        self.bom_table = QTableWidget()
        self.bom_table.setColumnCount(4)
        self.bom_table.setHorizontalHeaderLabels(["ID", "COMPONENT", "VALUE", "FOOTPRINT"])
        self.bom_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bom_table.setStyleSheet("""
            QTableWidget { background-color: #1e293b; color: #f1f5f9; gridline-color: #334155; border: none; font-size: 12px; }
            QHeaderView::section { background-color: #0f172a; color: #94a3b8; padding: 10px; border: none; font-weight: bold; font-size: 10px; }
            QTableWidget::item { padding: 10px; }
            QTableWidget::item:selected { background-color: #334155; color: #38bdf8; }
        """)
        self.tabs.addTab(self.bom_table, "BILL OF MATERIALS")

        layout.addWidget(self.tabs)

    def update_architecture(self, mermaid_code):
        self.arch_view.setPlainText(mermaid_code)
        self.tabs.setCurrentIndex(0)


    def update_bom(self, components):
        self.bom_table.setRowCount(len(components))
        for i, comp in enumerate(components):
            self.bom_table.setItem(i, 0, QTableWidgetItem(comp.get("id", "")))
            self.bom_table.setItem(i, 1, QTableWidgetItem(comp.get("type", "")))
            self.bom_table.setItem(i, 2, QTableWidgetItem(comp.get("value", "")))
            self.bom_table.setItem(i, 3, QTableWidgetItem(comp.get("footprint", "")))
        self.tabs.setCurrentIndex(2)

    def update_pcb(self, layout):
        self.pcb_scene.clear()
        
        # Draw Board Outline
        board = layout.get("board", {"x": 0, "y": 0, "width": 100, "height": 100})
        rect_item = QGraphicsRectItem(board["x"], board["y"], board["width"], board["height"])
        rect_item.setPen(QPen(QColor("#00ff00"), 2))
        rect_item.setBrush(QBrush(QColor(0, 50, 0, 150)))
        self.pcb_scene.addItem(rect_item)
        
        # Draw Components
        for comp in layout.get("components", []):
            cw, ch = 8, 8 # Default size
            if "MCU" in comp["type"].upper(): cw, ch = 15, 15
            elif "Res" in comp["type"] or "Cap" in comp["type"]: cw, ch = 5, 3
            
            c_rect = QGraphicsRectItem(comp["x"] - cw/2, comp["y"] - ch/2, cw, ch)
            c_rect.setPen(QPen(QColor("#ffffff"), 1))
            c_rect.setBrush(QBrush(QColor("#cc9900"))) # Gold/Copper color
            self.pcb_scene.addItem(c_rect)
            
            text = QGraphicsTextItem(comp["id"])
            text.setDefaultTextColor(QColor("#ffffff"))
            text.setFont(QFont("Arial", 6))
            text.setPos(comp["x"] - cw/2, comp["y"] - ch/2 - 5)
            self.pcb_scene.addItem(text)
            
        self.pcb_view.fitInView(self.pcb_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.tabs.setCurrentIndex(1)

    def clear(self):
        self.arch_view.clear()
        self.bom_table.setRowCount(0)
        self.pcb_scene.clear()
