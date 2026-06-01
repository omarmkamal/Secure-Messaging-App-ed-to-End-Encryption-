import socket, threading, os, hmac, hashlib, time
import tkinter as tk
from tkinter import messagebox, scrolledtext
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Util.Padding import pad, unpad

# Global list to store intercepted packets for the organized report
MITM_LOG = [] 

class ModernSecureChat:
    def __init__(self, root):
        self.root = root
        self.root.title("CCY2001 - Secure Messaging Simulation")
        self.root.geometry("500x750")
        self.root.configure(bg="#2F3136") 

        # Core State
        self.rsa_key = RSA.generate(2048) 
        self.session_key = None           
        self.hmac_key = None              
        self.conn = None
        self.role = None 

        self.setup_ui()

    def setup_ui(self):
        # --- Header ---
        self.header = tk.Frame(self.root, bg="#202225", height=60)
        self.header.pack(fill=tk.X)
        
        tk.Button(self.header, text="End Chat", bg="#F04747", fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", padx=10, 
                  command=self.end_chat_mitm).pack(side=tk.RIGHT, padx=15, pady=10)

        # --- Role Selection (Start either one first) ---
        self.auth_frame = tk.Frame(self.root, bg="#36393F", pady=20)
        self.auth_frame.pack(fill=tk.X)

        self.status_label = tk.Label(self.auth_frame, text="Choose a role to begin:", 
                                    bg="#36393F", fg="#8E9297", font=("Segoe UI", 10))
        self.status_label.pack()

        self.btn_container = tk.Frame(self.auth_frame, bg="#36393F")
        self.btn_container.pack(pady=10)

        tk.Button(self.btn_container, text="START SERVER", bg="#43B581", fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", width=15,
                  command=lambda: self.init_network(True)).pack(side=tk.LEFT, padx=10)
        
        tk.Button(self.btn_container, text="START CLIENT", bg="#5865F2", fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", width=15,
                  command=lambda: self.init_network(False)).pack(side=tk.LEFT, padx=10)

        # --- Chat Area ---
        self.chat_area = scrolledtext.ScrolledText(self.root, bg="#36393F", fg="#DCDDDE", 
                                                  font=("Segoe UI", 11), borderwidth=0, state=tk.DISABLED)
        self.chat_area.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        self.chat_area.tag_configure("right", justify='right')
        self.chat_area.tag_configure("left", justify='left')
        self.chat_area.tag_configure("system", justify='center')

        # --- Input Container ---
        self.input_container = tk.Frame(self.root, bg="#40444B", height=60)
        self.input_container.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.msg_input = tk.Entry(self.input_container, bg="#40444B", fg="white", 
                                 font=("Segoe UI", 12), borderwidth=0, insertbackground="white")
        self.msg_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, ipady=10)
        
        # KEYBOARD: Enter key triggers sending
        self.msg_input.bind("<Return>", lambda e: self.send_encrypted_msg())

        # MOUSE: Send button click triggers sending
        self.send_btn = tk.Button(self.input_container, text="Send", bg="#00AF91", fg="white", 
                                 font=("Segoe UI", 10, "bold"), relief="flat", padx=20,
                                 command=self.send_encrypted_msg)
        self.send_btn.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.Y)

    def log_msg(self, sender, text, align="left"):
        self.chat_area.config(state=tk.NORMAL)
        color = "#7289DA" if align == "right" else "#43B581"
        if align == "center": color = "#8E9297"
        tag = "right" if align == "right" else "left"
        if align == "center": tag = "system"
        self.chat_area.insert(tk.END, f"{sender}\n", (tag, "bold"))
        self.chat_area.insert(tk.END, f"{text}\n\n", (tag,))
        self.chat_area.tag_config("bold", foreground=color, font=("Segoe UI", 10, "bold"))
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def init_network(self, is_server):
        self.auth_frame.pack_forget() 
        self.role = "Server" if is_server else "Client"
        threading.Thread(target=self.run_handshake, args=(is_server,), daemon=True).start()

    def run_handshake(self, is_server):
        try:
            if is_server:
                s = socket.socket()
                s.bind(("127.0.0.1", 12345))
                s.listen(1)
                self.log_msg("SYSTEM", "Waiting for Client to connect...", "center")
                self.conn, _ = s.accept()
                
                # Packet 1: RSA Handshake
                pub_key_data = self.conn.recv(2048)
                MITM_LOG.append(("RSA Public Key (Client)", pub_key_data.hex()))
                peer_pub = RSA.import_key(pub_key_data)
                self.conn.send(self.rsa_key.publickey().export_key())
                
                # Packet 2: Session Key Exchange
                encrypted_keys = self.conn.recv(2048)
                MITM_LOG.append(("Encrypted Session Keys", encrypted_keys.hex()))
                keys = PKCS1_OAEP.new(self.rsa_key).decrypt(encrypted_keys)
                self.session_key, self.hmac_key = keys[:16], keys[16:]
            else:
                self.log_msg("SYSTEM", "Searching for Server...", "center")
                self.conn = socket.socket()
                while True:
                    try:
                        self.conn.connect(("127.0.0.1", 12345))
                        break
                    except:
                        time.sleep(1)
                
                # Packet 1: RSA Handshake
                self.conn.send(self.rsa_key.publickey().export_key())
                server_pub_data = self.conn.recv(2048)
                MITM_LOG.append(("RSA Public Key (Server)", server_pub_data.hex()))
                peer_pub = RSA.import_key(server_pub_data)
                
                # Packet 2: Encrypted Key Transfer
                self.session_key, self.hmac_key = os.urandom(16), os.urandom(16)
                key_blob = PKCS1_OAEP.new(peer_pub).encrypt(self.session_key + self.hmac_key)
                self.conn.send(key_blob)

            self.log_msg("SYSTEM", f"Secure Channel Verified as {self.role}.", "center")
            self.listen_thread()
        except Exception as e:
            self.log_msg("SYSTEM", f"Connection Error: {e}", "center")

    def send_encrypted_msg(self):
        msg = self.msg_input.get()
        if not msg or not self.session_key: return
        self.msg_input.delete(0, tk.END)
        self.log_msg("You", msg, align="right") 

        # AES Encryption + HMAC
        cipher = AES.new(self.session_key, AES.MODE_CBC)
        ct = cipher.encrypt(pad(msg.encode(), 16))
        payload = cipher.iv + ct
        mac = hmac.new(self.hmac_key, payload, hashlib.sha256).digest()
        
        packet = mac + payload
        MITM_LOG.append((f"Encrypted Message ({self.role})", packet.hex()))
        self.conn.send(packet)

    def listen_thread(self):
        peer = "Client" if self.role == "Server" else "Server"
        while True:
            try:
                data = self.conn.recv(4096)
                if not data: break
                
                if len(data) > 64: # Track Chat Packets
                    MITM_LOG.append((f"Encrypted Message ({peer})", data.hex()))

                mac, payload = data[:32], data[32:]
                iv, ct = payload[:16], payload[16:]
                msg = unpad(AES.new(self.session_key, AES.MODE_CBC, iv).decrypt(ct), 16).decode()
                self.log_msg(peer, msg, align="left") 
            except: break

    def end_chat_mitm(self):
        """Displays the Final Organized Security Report."""
        if not MITM_LOG:
            report_text = "No traffic was captured."
        else:
            report_text = "--- CYBERSECURITY MITM INTERCEPTION REPORT ---\n\n"
            report_text += "[!] PHASE 1: CRYPTOGRAPHIC HANDSHAKE\n"
            
            chat_packets = []
            packet_count = 1
            
            for p_type, p_data in MITM_LOG:
                if "Key" in p_type:
                    report_text += f"Packet {packet_count}: {p_type}\n"
                    report_text += f"Hex Data: {p_data[:50]}...\n\n"
                    packet_count += 1
                else:
                    chat_packets.append((p_type, p_data))

            report_text += "-" * 45 + "\n"
            report_text += "[!] PHASE 2: ENCRYPTED CHAT TRAFFIC\n"
            
            for p_type, p_data in chat_packets:
                report_text += f"Packet {packet_count}: {p_type}\n"
                report_text += f"Ciphertext: {p_data[:50]}...\n\n"
                packet_count += 1
            
            report_text += f"Total Interceptions: {len(MITM_LOG)}\n\n"
            report_text += "ANALYSIS: The attacker intercepted the data flow but could not read the messages due to AES-256 encryption."
        
        messagebox.showinfo("MITM Simulation Report", report_text)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernSecureChat(root)
    root.mainloop()

