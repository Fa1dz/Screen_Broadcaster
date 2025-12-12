import socket
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import io
import subprocess
import re

class ListenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Viewer - Socket Listener")
        self.root.geometry("1024x768")
        self.root.configure(bg="black")
        
        # Title
        tk.Label(self.root, text="Live Screen Viewer", fg="lime", bg="black", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Device discovery frame
        device_frame = tk.Frame(self.root, bg="black")
        device_frame.pack(pady=5)
        tk.Label(device_frame, text="Device:", fg="lime", bg="black").pack(side=tk.LEFT, padx=5)
        
        self.device_var = tk.StringVar(value="127.0.0.1")
        self.device_combo = tk.OptionMenu(device_frame, self.device_var, "127.0.0.1")
        self.device_combo.config(bg="black", fg="lime")
        self.device_combo.pack(side=tk.LEFT, padx=5)
        
        # Refresh devices button
        self.refresh_btn = tk.Button(device_frame, text="Refresh Devices", command=self.refresh_devices, bg="lime", fg="black", font=("Arial", 9))
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Port entry
        port_frame = tk.Frame(self.root, bg="black")
        port_frame.pack(pady=5)
        tk.Label(port_frame, text="Port:", fg="lime", bg="black").pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(port_frame, bg="black", fg="lime", width=10)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Start/Stop button
        self.start_btn = tk.Button(self.root, text="Start Listening", command=self.toggle_listening, bg="lime", fg="black", font=("Arial", 10, "bold"))
        self.start_btn.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Status: Stopped", fg="red", bg="black")
        self.status_label.pack(pady=5)
        
        # Video display
        self.video_label = tk.Label(self.root, bg="black", fg="lime", text="Waiting for stream...", font=("Arial", 12))
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Stats label
        self.stats_label = tk.Label(self.root, text="Frames: 0 | Bytes: 0 KB | FPS: 0", fg="cyan", bg="black")
        self.stats_label.pack(pady=5)
        
        self.listening = False
        self.server_socket = None
        self.frames_received = 0
        self.bytes_received = 0
        self.last_frame_time = 0
        
        # Auto-discover devices on startup
        self.root.after(500, self.refresh_devices)
    
    def scan_network_for_senders(self):
        """Scan local network for devices running the sender program."""
        devices = []
        
        # Get local IP address
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Extract network prefix (e.g., 192.168.1.x)
            network_prefix = ".".join(local_ip.split(".")[:3]) + "."
        except:
            network_prefix = "192.168.1."
        
        # Scan ports on common IPs
        for i in range(1, 255):
            ip = network_prefix + str(i)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, 5000))
                sock.close()
                
                if result == 0:
                    devices.append(ip)
            except:
                pass
        
        return devices
    
    def refresh_devices(self):
        """Scan for devices and update dropdown."""
        self.status_label.config(text="Status: Scanning for devices...", fg="yellow")
        self.root.update()
        
        t = threading.Thread(target=self._scan_thread, daemon=True)
        t.start()
    
    def _scan_thread(self):
        """Run device scan in background."""
        try:
            devices = self.scan_network_for_senders()
            
            if devices:
                # Update dropdown menu
                menu = self.device_combo['menu']
                menu.delete(0, 'end')
                
                for device in devices:
                    menu.add_command(label=device, command=lambda d=device: self.device_var.set(d))
                
                # Also add localhost
                menu.add_command(label="127.0.0.1", command=lambda: self.device_var.set("127.0.0.1"))
                
                # Set to first device found
                self.device_var.set(devices[0])
                self.status_label.config(text=f"Status: Found {len(devices)} device(s)", fg="lime")
            else:
                self.status_label.config(text="Status: No devices found (using localhost)", fg="yellow")
                self.device_var.set("127.0.0.1")
        except Exception as e:
            self.status_label.config(text=f"Status: Scan error - {str(e)}", fg="red")
    
    def toggle_listening(self):
        """Start or stop listening."""
        if self.listening:
            self.stop_listening()
        else:
            self.start_listening()
    
    def start_listening(self):
        """Start listening for incoming stream."""
        port_str = self.port_entry.get().strip()
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return
        
        ip = self.device_var.get().strip()
        if not ip:
            messagebox.showerror("Error", "Please select a device IP.")
            return
        
        self.listening = True
        self.start_btn.config(text="Stop Listening")
        self.port_entry.config(state="disabled")
        self.device_combo.config(state="disabled")
        self.refresh_btn.config(state="disabled")
        self.frames_received = 0
        self.bytes_received = 0
        
        t = threading.Thread(target=self.listen_thread, args=(ip, port), daemon=True)
        t.start()
    
    def listen_thread(self, ip, port):
        """Listen for incoming video stream."""
        try:
            self.status_label.config(text=f"Connecting to {ip}:{port}...", fg="yellow")
            self.root.update()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((ip, port))
            
            self.status_label.config(text=f"Connected: {ip}:{port}", fg="lime")
            
            while self.listening:
                try:
                    # Receive frame size (4 bytes)
                    size_data = sock.recv(4)
                    if not size_data:
                        break
                    
                    frame_size = int.from_bytes(size_data, byteorder='big')
                    
                    # Receive frame data
                    frame_data = b''
                    while len(frame_data) < frame_size:
                        chunk = sock.recv(min(4096, frame_size - len(frame_data)))
                        if not chunk:
                            break
                        frame_data += chunk
                    
                    if len(frame_data) == frame_size:
                        # Decode frame
                        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            # Convert to RGB and PIL Image
                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            pil_image = Image.fromarray(rgb_frame)
                            
                            # Resize to fit window
                            pil_image.thumbnail((990, 650), Image.Resampling.LANCZOS)
                            
                            # Convert to PhotoImage
                            photo = ImageTk.PhotoImage(pil_image)
                            
                            # Update label
                            def _update_video():
                                self.video_label.config(image=photo, text="")
                                self.video_label.image = photo
                            self.root.after(0, _update_video)
                            
                            self.frames_received += 1
                            self.bytes_received += frame_size
                            
                            # Calculate FPS
                            import time
                            current_time = time.time()
                            if self.last_frame_time > 0:
                                fps = 1.0 / (current_time - self.last_frame_time)
                            else:
                                fps = 0
                            self.last_frame_time = current_time
                            
                            # Update stats
                            def _update_stats():
                                self.stats_label.config(text=f"Frames: {self.frames_received} | Bytes: {self.bytes_received // 1024} KB | FPS: {fps:.1f}")
                            self.root.after(0, _update_stats)
                
                except Exception as e:
                    break
            
            sock.close()
        
        except socket.timeout:
            self.status_label.config(text="Error: Connection timeout", fg="red")
        except ConnectionRefusedError:
            self.status_label.config(text="Error: Connection refused (sender not running?)", fg="red")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", fg="red")
        
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop listening."""
        self.listening = False
        self.status_label.config(text="Status: Stopped", fg="red")
        self.start_btn.config(text="Start Listening")
        self.port_entry.config(state="normal")
        self.device_combo.config(state="normal")
        self.refresh_btn.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = ListenerApp(root)
    root.mainloop()