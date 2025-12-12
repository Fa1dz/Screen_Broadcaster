import socket
import tkinter as tk
from tkinter import messagebox
import threading
import cv2
import numpy as np
from PIL import ImageGrab
import time

class SenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Broadcaster")
        self.root.geometry("600x400")
        self.root.configure(bg="black")
        
        # Title
        tk.Label(self.root, text="Live Screen Broadcaster", fg="lime", bg="black", font=("Arial", 14, "bold")).pack(pady=10)
        
        # IP entry
        ip_frame = tk.Frame(self.root, bg="black")
        ip_frame.pack(pady=5)
        tk.Label(ip_frame, text="Target IP:", fg="lime", bg="black").pack(side=tk.LEFT, padx=5)
        self.ip_entry = tk.Entry(ip_frame, bg="black", fg="lime", width=20)
        self.ip_entry.insert(0, "192.168.56.1")
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        
        # Port entry
        port_frame = tk.Frame(self.root, bg="black")
        port_frame.pack(pady=5)
        tk.Label(port_frame, text="Port:", fg="lime", bg="black").pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(port_frame, bg="black", fg="lime", width=20)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        # Quality slider
        quality_frame = tk.Frame(self.root, bg="black")
        quality_frame.pack(pady=5)
        tk.Label(quality_frame, text="Quality:", fg="lime", bg="black").pack(side=tk.LEFT, padx=5)
        self.quality_slider = tk.Scale(quality_frame, from_=10, to=95, orient=tk.HORIZONTAL, bg="black", fg="lime", length=150)
        self.quality_slider.set(70)
        self.quality_slider.pack(side=tk.LEFT, padx=5)
        
        # FPS entry
        fps_frame = tk.Frame(self.root, bg="black")
        fps_frame.pack(pady=5)
        tk.Label(fps_frame, text="FPS:", fg="lime", bg="black").pack(side=tk.LEFT, padx=5)
        self.fps_entry = tk.Entry(fps_frame, bg="black", fg="lime", width=10)
        self.fps_entry.insert(0, "10")
        self.fps_entry.pack(side=tk.LEFT, padx=5)
        
        # Start/Stop button
        self.broadcast_btn = tk.Button(self.root, text="Start Broadcasting", command=self.toggle_broadcast, bg="lime", fg="black", font=("Arial", 10, "bold"))
        self.broadcast_btn.pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Status: Idle", fg="red", bg="black", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # Stats label
        self.stats_label = tk.Label(self.root, text="Frames sent: 0 | Bytes: 0 KB", fg="cyan", bg="black")
        self.stats_label.pack(pady=5)
        
        self.broadcasting = False
        self.frames_sent = 0
        self.bytes_sent = 0
        self.socket = None
    
    def toggle_broadcast(self):
        """Start or stop broadcasting."""
        if self.broadcasting:
            self.stop_broadcast()
        else:
            self.start_broadcast()
    
    def start_broadcast(self):
        """Start broadcasting screen."""
        ip = self.ip_entry.get().strip()
        port_str = self.port_entry.get().strip()
        
        if not ip:
            messagebox.showerror("Error", "Please enter a target IP address.")
            return
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number.")
            return
        
        try:
            fps_str = self.fps_entry.get().strip()
            fps = int(fps_str) if fps_str else 10
        except ValueError:
            fps = 10
        
        self.broadcasting = True
        self.broadcast_btn.config(text="Stop Broadcasting")
        self.frames_sent = 0
        self.bytes_sent = 0
        
        t = threading.Thread(target=self.broadcast_thread, args=(ip, port, fps), daemon=True)
        t.start()
    
    def broadcast_thread(self, ip, port, fps):
        """Broadcast screen in a background thread."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            
            self.status_label.config(text=f"Status: Connecting to {ip}:{port}...", fg="yellow")
            self.root.update()
            
            self.socket.connect((ip, port))
            
            self.status_label.config(text=f"Status: Broadcasting to {ip}:{port}", fg="lime")
            
            delay = 1.0 / fps
            quality = self.quality_slider.get()
            
            while self.broadcasting:
                try:
                    # Capture screen
                    screen = ImageGrab.grab()
                    frame = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
                    
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    data = buffer.tobytes()
                    
                    # Send frame size (4 bytes) followed by frame data
                    size = len(data).to_bytes(4, byteorder='big')
                    self.socket.sendall(size + data)
                    
                    self.frames_sent += 1
                    self.bytes_sent += len(data)
                    
                    # Update stats
                    def _update_stats():
                        self.stats_label.config(text=f"Frames sent: {self.frames_sent} | Bytes: {self.bytes_sent // 1024} KB")
                    self.root.after(0, _update_stats)
                    
                    time.sleep(delay)
                
                except Exception as e:
                    self.status_label.config(text=f"Status: Error sending frame", fg="red")
                    self.root.update()
                    break
        
        except socket.timeout:
            self.status_label.config(text="Status: Connection timeout", fg="red")
            self.root.update()
            messagebox.showerror("Error", f"Connection timeout: Could not reach {ip}:{port}")
        except ConnectionRefusedError:
            self.status_label.config(text="Status: Connection refused", fg="red")
            self.root.update()
            messagebox.showerror("Error", f"Connection refused: Make sure listener is running on {ip}:{port}")
        except Exception as e:
            self.status_label.config(text="Status: Error", fg="red")
            self.root.update()
            messagebox.showerror("Error", f"Broadcast failed: {e}")
        finally:
            self.stop_broadcast()
    
    def stop_broadcast(self):
        """Stop broadcasting."""
        self.broadcasting = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.status_label.config(text="Status: Stopped", fg="red")
        self.broadcast_btn.config(text="Start Broadcasting")

if __name__ == "__main__":
    root = tk.Tk()
    app = SenderApp(root)
    root.mainloop()