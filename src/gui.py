import sys
import threading
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QComboBox, QStatusBar, QFrame, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt, QSize, Signal, QObject
from PySide6.QtGui import QFont, QColor, QPalette
from src.bridge import GenerationBridge
from src.canvas_view import CanvasView
from PySide6.QtWidgets import QSplitter

class WorkerSignals(QObject):
    log = Signal(str)
    finished = Signal(bool, str)
    update_arch = Signal(str)
    update_bom = Signal(list)
    update_pcb = Signal(dict)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KiCad AI Hardware Generator")
        self.setMinimumSize(QSize(950, 750))
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #e0e0e0; font-size: 14px; }
            QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d; border-radius: 8px; padding: 10px; font-size: 15px; }
            QLineEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d; border-radius: 4px; padding: 8px; font-size: 13px; }
            QPushButton { background-color: #0078d4; color: white; border-radius: 6px; padding: 12px; font-weight: bold; }
            QPushButton#btn_generate { background-color: #28a745; }
            QComboBox { background-color: #333333; color: white; border: 1px solid #444444; padding: 5px; }
            QFrame#separator { background-color: #3d3d3d; }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(15)

        title_label = QLabel("🚀 KiFlow AI Canvas")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        main_layout.addWidget(title_label)

        # Main Content with Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel (Controls and Logs)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 10, 0)

        # Config Section (API Key)
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("OpenRouter API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Cole sua chave sk-or-v1-... aqui")
        # Tenta carregar do env se existir
        if os.getenv("OPENROUTER_API_KEY"):
            self.api_key_input.setText(os.getenv("OPENROUTER_API_KEY"))
        config_layout.addWidget(self.api_key_input)
        main_layout.addLayout(config_layout)

        main_layout.addWidget(QLabel("Descreva seu hardware:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Ex: Um divisor de tensão com dois resistores de 10k...")
        main_layout.addWidget(self.prompt_input)

        control_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True) # Permite digitar qualquer um dos 37+ modelos
        self.model_combo.addItems([
            "AUTO", 
            "xiaomi/mimo-v2-flash:free",
            "google/gemini-2.0-flash-exp:free",
            "mistralai/pixtral-12b:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "allenai/olmo-7b-instruct:free",
            "openrouter/auto",
            "gpt-4o", 
            "gpt-3.5-turbo", 
            "Ollama"
        ])
        self.model_combo.setPlaceholderText("Digite o ID do modelo (ex: google/gemini-pro)")
        control_layout.addWidget(QLabel("Modelo:"))
        control_layout.addWidget(self.model_combo)
        control_layout.addStretch()
        
        self.btn_generate = QPushButton("GERAR PROJETO COMPLETO")
        self.btn_generate.setObjectName("btn_generate")
        self.btn_generate.setMinimumWidth(200)
        self.btn_generate.clicked.connect(self.start_generation)
        control_layout.addWidget(self.btn_generate)
        main_layout.addLayout(control_layout)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(180)
        self.log_output.setStyleSheet("background-color: #000000; color: #00ff00; font-family: 'Consolas'; font-size: 13px;")
        self.left_layout.addWidget(self.log_output)
        
        # Right Panel (Canvas)
        self.canvas = CanvasView()
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.canvas)
        self.splitter.setStretchFactor(1, 2) # Canvas gets more space
        
        main_layout.addWidget(self.splitter)
        
        self.statusBar().showMessage("Sistema Pronto")

    def append_log(self, text):
        self.log_output.moveCursor(Qt.TextCursor.End)
        self.log_output.insertPlainText(text if text.startswith("\n") else f" {text}")
        self.log_output.moveCursor(Qt.TextCursor.End)


    def start_generation(self):
        prompt = self.prompt_input.toPlainText().strip()
        api_key = self.api_key_input.text().strip()
        
        if not prompt:
            QMessageBox.warning(self, "Aviso", "Por favor, descreva o circuito.")
            return

        if api_key:
            os.environ["OPENROUTER_API_KEY"] = api_key
            os.environ["LLM_API_KEY"] = api_key # Compatibilidade

        self.btn_generate.setEnabled(False)
        self.log_output.clear()
        self.canvas.clear()
        model = self.model_combo.currentText()
        
        self.signals = WorkerSignals()
        self.signals.log.connect(self.append_log)
        self.signals.finished.connect(self.on_finished)
        self.signals.update_arch.connect(self.canvas.update_architecture)
        self.signals.update_bom.connect(self.canvas.update_bom)
        self.signals.update_pcb.connect(self.canvas.update_pcb)
        
        threading.Thread(target=self.run_bridge, args=(prompt, model)).start()

    def run_bridge(self, prompt, model):
        cwd = os.getcwd()
        bridge = GenerationBridge(model=model)
        self.signals.log.emit(f"Modo: {model} | Destino: {cwd}")
        
        # Callbacks para o canvas
        def canvas_callback(type, data):
            if type == "arch": self.signals.update_arch.emit(data)
            elif type == "bom": self.signals.update_bom.emit(data)
            elif type == "pcb": self.signals.update_pcb.emit(data)

        success, message = bridge.process(prompt, callback=self.signals.log.emit, canvas_callback=canvas_callback)
        self.signals.finished.emit(success, message)

    def on_finished(self, success, message):
        self.btn_generate.setEnabled(True)
        if success:
            QMessageBox.information(self, "Sucesso", message)
            self.statusBar().showMessage("Geração Concluída")
        else:
            QMessageBox.critical(self, "Erro", message)
            self.statusBar().showMessage("Falha na geração")



def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
