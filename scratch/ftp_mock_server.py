import socket
import threading
import os
import sys

class MockFTPServer:
    def __init__(self, host="127.0.0.1", port=2121):
        self.host = host
        self.port = port
        self.base_dir = "/tmp/ftp_root"
        os.makedirs(self.base_dir, exist_ok=True)
        # Create directories for the users
        os.makedirs(os.path.join(self.base_dir, "netzwerk_user", "netzwerkpunkt.de", "httpdocs"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "feen_user", "königlichesfeenreich.de", "httpdocs"), exist_ok=True)
        
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Mock FTP Server listening on {self.host}:{self.port}...")
        
        while True:
            try:
                client_sock, addr = self.server_socket.accept()
                print(f"Accepted connection from {addr}")
                threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True).start()
            except Exception as e:
                print(f"Server error: {e}")
                break

    def handle_client(self, sock):
        sock.sendall(b"220 Mock FTP Server Ready\r\n")
        cwd = "/"
        user = None
        data_port = None
        
        while True:
            try:
                data = sock.recv(1024)
                if not data:
                    break
                line = data.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                print(f"FTP Client -> {line}")
                parts = line.split(None, 1)
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""
                
                if cmd == "USER":
                    user = arg
                    sock.sendall(b"331 User name okay, need password.\r\n")
                elif cmd == "PASS":
                    sock.sendall(b"230 User logged in, proceed.\r\n")
                elif cmd == "SYST":
                    sock.sendall(b"215 UNIX Type: L8\r\n")
                elif cmd == "PWD":
                    sock.sendall(f"257 \"{cwd}\" is current directory.\r\n".encode())
                elif cmd == "TYPE":
                    sock.sendall(b"200 Type set to I.\r\n")
                elif cmd == "CWD":
                    # Simple CWD handling
                    cwd = arg
                    sock.sendall(b"250 Directory successfully changed.\r\n")
                elif cmd == "PASV":
                    # Open a random passive data socket
                    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    data_sock.bind((self.host, 0))
                    data_sock.listen(1)
                    p_port = data_sock.getsockname()[1]
                    p1 = p_port // 256
                    p2 = p_port % 256
                    ip_parts = self.host.split(".")
                    sock.sendall(f"227 Entering Passive Mode ({','.join(ip_parts)},{p1},{p2})\r\n".encode())
                    
                    # Accept connection on data socket in a separate threat/timeout
                    data_conn, _ = data_sock.accept()
                    data_sock.close()
                elif cmd == "STOR":
                    filename = os.path.basename(arg)
                    sock.sendall(b"150 File status okay; about to open data connection.\r\n")
                    
                    # Write files to target directories
                    user_dir = "netzwerk_user" if user == "netzwerk_user" else "feen_user"
                    domain_dir = "netzwerkpunkt.de" if user == "netzwerk_user" else "königlichesfeenreich.de"
                    target_dir = os.path.join(self.base_dir, user_dir, domain_dir, "httpdocs")
                    os.makedirs(target_dir, exist_ok=True)
                    
                    target_path = os.path.join(target_dir, filename)
                    with open(target_path, "wb") as f:
                        while True:
                            chunk = data_conn.recv(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    data_conn.close()
                    print(f"Saved file {filename} to {target_path}")
                    sock.sendall(b"226 Closing data connection.\r\n")
                elif cmd == "QUIT":
                    sock.sendall(b"221 Goodbye.\r\n")
                    break
                else:
                    sock.sendall(b"502 Command not implemented.\r\n")
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        sock.close()

if __name__ == "__main__":
    server = MockFTPServer()
    server.start()
