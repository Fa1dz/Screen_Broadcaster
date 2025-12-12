import socket
import tkinter as tk
from tkinter import scrolledtext
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import io

class ListenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Viewer - Socket Listener")
        self.root.geometry("1024x768")
        self.root.configure(bg="black")
        
        # Title
        tk.Label(self.root, text="Live Screen Viewer", fg="lime", bg="black", font=("Arial", 14, "bold")).pack(pady=10)
        
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
        self.stats_label = tk.Label(self.root, text="Frames: 0 | Bytes: 0 KB", fg="cyan", bg="black")
        self.stats_label.pack(pady=5)
        
        self.listening = False
        self.server_socket = None
        self.frames_received = 0
        self.bytes_received = 0
    
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
            return
        
        self.listening = True
        self.start_btn.config(text="Stop Listening")
        self.port_entry.config(state="disabled")
        self.frames_received = 0
        self.bytes_received = 0
        
        t = threading.Thread(target=self.listen_thread, args=(port,), daemon=True)
        t.start()
    
    def listen_thread(self, port):
        """Listen for incoming video stream."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", port))
            self.server_socket.listen(1)
            
            self.status_label.config(text=f"Listening on port {port}", fg="lime")
            
            conn, addr = self.server_socket.accept()
            self.status_label.config(text=f"Connected: {addr}", fg="lime")
            
            while self.listening:
                try:
                    # Receive frame size (4 bytes)
                    size_data = conn.recv(4)
                    if not size_data:
                        break
                    
                    frame_size = int.from_bytes(size_data, byteorder='big')
                    
                    # Receive frame data
                    frame_data = b''
                    while len(frame_data) < frame_size:
                        chunk = conn.recv(min(4096, frame_size - len(frame_data)))
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
                            self.video_label.config(image=photo, text="")
                            self.video_label.image = photo  # Keep a reference
                            
                            self.frames_received += 1
                            self.bytes_received += frame_size
                            
                            # Update stats
                            self.stats_label.config(text=f"Frames: {self.frames_received} | Bytes: {self.bytes_received // 1024} KB")
                
                except Exception as e:
                    break
            
            conn.close()
        
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", fg="red")
        
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop listening."""
        self.listening = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        self.status_label.config(text="Status: Stopped", fg="red")
        self.start_btn.config(text="Start Listening")
        self.port_entry.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = ListenerApp(root)
    root.mainloop()