import logging
import re
import socket
import threading

HOST = "127.0.0.1"
PORT = 17070
clients = {}
COMMAND_PATTERNS = {
    "help": r"^/help$",
    "alias": r"^/alias\s+(\w+)$",
    "whisper": r"^/whisper\s+(\w+)\s+(.+)$",
    "broadcast": r"^(.+)$"
}

logger = logging.getLogger(__name__)

def is_username_taken(username):
    for addr in clients:
        if username == clients[addr]["username"]:
            return True
    return False

def get_addr_by_username(username):
    for addr in clients:
        client = clients[addr]
        if client["username"] == username:
            return addr
    return None

def help(addr):
    help_message = ("Available commands:\n" +
                    "- /alias [name]\n" +
                    "- /whisper [name] [message]\n" +
                    "- /broadcast [message]\n")
    clients[addr]["socket"].send(help_message.encode("utf-8"))
    logger.info(f"{addr[0]}:{addr[1]} asked for the help menu")

def alias(addr, username):
    client = clients[addr]
    if not is_username_taken(username):
        client["username"] = username
        client["socket"].send(f"Your name is now {username}\n".encode("utf-8"))
        logger.info(f"{addr[0]}:{addr[1]} changed their alias to {username}")
    else:
        client["socket"].send(f"Username {username} is already taken.\n".encode("utf-8"))
        logger.info(f"{addr[0]}:{addr[1]} tried to switch their alias to {username} which was already taken")

def send_message(recipient_socket, message):
    recipient_socket.send(message.encode("utf-8"))

def whisper(sender_addr, recipient_username, message):
    sender_username = clients[sender_addr]["username"]
    rec_addr = get_addr_by_username(recipient_username)
    if rec_addr:
        send_message(clients[rec_addr]["socket"], f"{sender_username} whispers to you : {message}\n")
        logger.info(f"{sender_addr[0]}:{sender_addr[1]} sent a whisper to {rec_addr[0]}:{rec_addr[1]} : {message}")
    else:
        clients[sender_addr]["socket"].send(f"There is no client with username {recipient_username}\n".encode("utf8"))
        logger.info(f"{sender_addr[0]}:{sender_addr[1]} tried to whisper to {recipient_username} without success : {message}")

def broadcast(sender_addr, message):
    sender_username = clients[sender_addr]["username"]
    message = f"{sender_username} says : {message[0]}\n"
    # L'émetteur ne reçoit pas son broadcast
    recipients = filter(lambda ad: ad != sender_addr, clients)
    list(map(lambda rec_addr: send_message(clients[rec_addr]["socket"], message), recipients))
    logger.info(f"{sender_addr[0]}:{sender_addr[1]} sent a broadcast : {message}")

def parse_command(client_input):
    for command, pattern in COMMAND_PATTERNS.items():
        match = re.match(pattern, client_input)
        if match:
            return command, match.groups()
    return None, None

def handle_input(client_addr, client_input):
    command, args = parse_command(client_input)
    if command == "help":
        help(client_addr)
    elif command == "alias":
        alias(client_addr, args[0])
    elif command == "whisper":
        whisper(client_addr, args[0], args[1])
    elif command == "broadcast":
        broadcast(client_addr, args)

def handle_client(client_socket, client_addr):
    clients[client_addr] = {"username": f"{client_addr[0]}:{client_addr[1]}", "socket": client_socket}
    logger.info(f"{client_addr} connected")
    print(f"{client_addr} connected")
    try:
        while True:
            client_bytes = client_socket.recv(1024)
            # Si recv ne récupère rien, ça veut dire que le client est déconnecté
            if not client_bytes:
                break
            handle_input(client_addr, client_bytes.decode("utf8"))
    except ConnectionResetError:
        print(f"{client_addr} crashed")
    finally:
        del clients[client_addr]
        client_socket.close()
        logger.info(f"{client_addr} disconnected")
        print(f"{client_addr} disconnected")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        server.listen(4) # Accepte un maximum de 4 connexions simultanées
        logger.info(f"Server started on {HOST}:{PORT}")
        print(f"Listening on {HOST}:{PORT}")

        # Tourne tant que le KeyboardInterrupt n'est pas déclenché
        while True:
            client_socket, client_addr = server.accept()
            # Crée un nouveau thread géré par new_client()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_addr))
            client_thread.start()
    except KeyboardInterrupt:
        logger.info("Server shut down")
        print("Shutting down server")
    except OSError:
        print("Server still running. Shutting it down now.")
    finally:
        server.close()

if __name__ == '__main__':
    logging.basicConfig(format="[%(asctime)s] %(levelname)s:%(message)s", datefmt="%m/%d/%Y %I:%M:%S %p", filename="socket_server.log", level=logging.INFO)
    start_server()
