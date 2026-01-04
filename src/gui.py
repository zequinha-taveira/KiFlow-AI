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
            QMainWindow { background-color: #0f172a; }
            QWidget { color: #f8fafc; font-family: 'Inter', 'Segoe UI', sans-serif; }
            
            QLabel { color: #94a3b8; font-size: 14px; font-weight: 500; }
            QLabel#title { color: #f1f5f9; font-weight: 800; font-size: 28px; }
            
            QTextEdit { 
                background-color: #1e293b; 
                color: #f1f5f9; 
                border: 1px solid #334155; 
                border-radius: 12px; 
                padding: 12px; 
                font-size: 14px; 
                selection-background-color: #38bdf8;
            }
            QTextEdit:focus { border: 1px solid #38bdf8; background-color: #0f172a; }

            QLineEdit { 
                background-color: #1e293b; 
                color: #f1f5f9; 
                border: 1px solid #334155; 
                border-radius: 8px; 
                padding: 10px; 
                font-size: 13px; 
            }
            QLineEdit:focus { border: 1px solid #818cf8; }

            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #7c3aed);
                color: white; 
                border-radius: 10px; 
                padding: 14px; 
                font-weight: bold; 
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6); }
            QPushButton:pressed { background: #4338ca; }
            
            QPushButton#btn_generate { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #06b6d4, stop:1 #3b82f6); 
                font-size: 15px;
                letter-spacing: 1px;
            }
            QPushButton#btn_generate:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22d3ee, stop:1 #60a5fa); }
            QPushButton#btn_generate:disabled { background: #1e293b; color: #475569; }

            QComboBox { 
                background-color: #1e293b; 
                color: #f1f5f9; 
                border: 1px solid #334155; 
                border-radius: 8px; 
                padding: 8px; 
                min-width: 150px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #1e293b; color: #f1f5f9; selection-background-color: #334155; }

            QStatusBar { background: #0f172a; color: #94a3b8; border-top: 1px solid #1e293b; }
            QScrollBar:vertical { border: none; background: #0f172a; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #334155; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title_label = QLabel("🌊 KiFlow AI")
        title_label.setObjectName("title")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        status_indicator = QLabel("● SYSTEM READY")
        status_indicator.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(status_indicator)
        main_layout.addLayout(header_layout)

        # Main Content with Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        
        # Left Panel (Controls and Logs)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 15, 0)
        self.left_layout.setSpacing(15)

        # Config Section
        config_group = QVBoxLayout()
        config_group.addWidget(QLabel("OPENROUTER / AI API KEY"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your API Key...")
        if os.getenv("OPENROUTER_API_KEY"):
            self.api_key_input.setText(os.getenv("OPENROUTER_API_KEY"))
        config_group.addWidget(self.api_key_input)
        self.left_layout.addLayout(config_group)

        self.left_layout.addWidget(QLabel("PROMPT DO HARDWARE"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Ex: Um teclado mecânico com Raspberry Pi Pico e USB-C...")
        self.left_layout.addWidget(self.prompt_input)

        # Model and Action
        model_action_layout = QHBoxLayout()
        model_vbox = QVBoxLayout()
        
        model_header_layout = QHBoxLayout()
        model_header_layout.addWidget(QLabel("MODELO"))
        model_header_layout.addStretch()
        
        manage_keys_link = QLabel('<a href="https://openrouter.ai/keys" style="color: #38bdf8; text-decoration: none; font-size: 10px;">Manage your API keys</a>')
        manage_keys_link.setOpenExternalLinks(True)
        model_header_layout.addWidget(manage_keys_link)
        
        model_vbox.addLayout(model_header_layout)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "AUTO", 
            "google/gemini-2.0-flash-exp:free",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "deepseek/deepseek-r1",
            "mistralai/mistral-large-2",
            "Ollama"
        ])
        model_vbox.addWidget(self.model_combo)
        model_action_layout.addLayout(model_vbox)
        
        self.btn_generate = QPushButton("GERAR PROJETO")
        self.btn_generate.setObjectName("btn_generate")
        self.btn_generate.setMinimumWidth(180)
        self.btn_generate.clicked.connect(self.start_generation)
        model_action_layout.addWidget(self.btn_generate, 0, Qt.AlignBottom)
        self.left_layout.addLayout(model_action_layout)

        # Log Section
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(200)
        self.log_output.setStyleSheet("""
            background-color: #020617; 
            color: #38bdf8; 
            font-family: 'Fira Code', 'Consolas', monospace; 
            font-size: 12px;
            border: 1px solid #1e293b;
        """)
        self.left_layout.addWidget(self.log_output)
        
        # Right Panel (Canvas)
        self.canvas = CanvasView()
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.canvas)
        self.splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(self.splitter)
        
        self.statusBar().showMessage("Ready to build hardware")
        self.statusBar().setStyleSheet("background: #0f172a; color: #64748b; padding-left: 10px;")


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
