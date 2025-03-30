import psutil
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import csv
from datetime import datetime
import platform

# ------------------ Constants ------------------
REFRESH_INTERVAL = 5000  # 5 seconds
GRAPH_DATA_POINTS = 50
ALERT_THRESHOLDS = {'cpu': 80, 'memory': 80, 'disk': 90, 'network': 80}
LOG_FILE = "process_monitor.log"

# ------------------ Utility Functions ------------------
def log_action(message):
    """Log actions to a file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def validate_priority(value):
    """Validate nice value based on OS"""
    if platform.system() == "Windows":
        return max(-20, min(value, 20))  # Windows has different priority classes
    return max(-20, min(value, 19))  # Standard Unix nice values

# ------------------ ProcessMonitor Class ------------------
class ProcessMonitor:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        self.setup_theme()
        self.running = True
        self.paused = False
        self.alerts_muted = False
        self.cpu_usage = []
        self.mem_usage = []
        self.disk_usage = []
        self.net_usage = []
        self.start_threads()
        self.update_process_list()

    def setup_ui(self):
        """Setup the main UI components"""
        self.root.title("Real-Time Process Monitor")
        self.root.geometry("1200x800")
        
        # Configure styles
        self.style = ttk.Style()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Processes
        self.process_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.process_frame, text="Processes")
        self.setup_process_tab()
        
        # Tab 2: Performance
        self.perf_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.perf_frame, text="Performance")
        self.setup_performance_tab()
        
        # Tab 3: System Info
        self.sys_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sys_frame, text="System Info")
        self.setup_system_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        self.status_bar.pack(fill="x", side="bottom")
        self.status_var.set("Ready. Monitoring processes...")

    def setup_process_tab(self):
        """Setup the processes tab"""
        # Filter/Search frame
        filter_frame = ttk.Frame(self.process_frame)
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Search:").pack(side="left")
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.debounced_filter)
        
        # Add search button here
        search_btn = ttk.Button(filter_frame, text="Search", command=self.update_process_list)
        search_btn.pack(side="left", padx=5)
        
        self.search_by = ttk.Combobox(filter_frame, values=["Name", "PID", "User"], state="readonly")
        self.search_by.pack(side="left", padx=5)
        self.search_by.set("Name")
        
        # Button frame
        btn_frame = ttk.Frame(self.process_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Kill Process", command=self.kill_process).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Lower Priority", command=lambda: self.change_priority(10)).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Raise Priority", command=lambda: self.change_priority(-10)).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Pause Updates", command=self.toggle_pause).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Mute Alerts", command=self.toggle_mute_alerts).pack(side="left", padx=2)
        
        # Process treeview
        self.tree_frame = ttk.Frame(self.process_frame)
        self.tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        columns = ("PID", "Name", "User", "CPU%", "Memory (MB)", "Priority", "Threads")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=100)
        
        self.tree.pack(fill="both", expand=True, side="left")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Right-click menu
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="Kill Process", command=self.kill_process)
        self.tree_menu.add_command(label="Details", command=self.show_process_details)
        self.tree.bind("<Button-3>", self.show_tree_menu)

    def setup_performance_tab(self):
        """Setup the performance monitoring tab"""
        # Create matplotlib figures
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(10, 6))
        plt.subplots_adjust(hspace=0.5)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.perf_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Threshold controls
        threshold_frame = ttk.Frame(self.perf_frame)
        threshold_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(threshold_frame, text="Alert Thresholds:").pack(side="left")
        
        self.cpu_thresh = tk.IntVar(value=ALERT_THRESHOLDS['cpu'])
        ttk.Label(threshold_frame, text="CPU%:").pack(side="left", padx=(10, 0))
        ttk.Entry(threshold_frame, textvariable=self.cpu_thresh, width=5).pack(side="left")
        
        self.mem_thresh = tk.IntVar(value=ALERT_THRESHOLDS['memory'])
        ttk.Label(threshold_frame, text="Memory%:").pack(side="left", padx=(10, 0))
        ttk.Entry(threshold_frame, textvariable=self.mem_thresh, width=5).pack(side="left")
        
        ttk.Button(threshold_frame, text="Update Thresholds", command=self.update_thresholds).pack(side="left", padx=10)

    def setup_system_tab(self):
        """Setup the system information tab"""
        # System info frame
        sys_info_frame = ttk.LabelFrame(self.sys_frame, text="System Information")
        sys_info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # System info labels
        info = [
            ("System", platform.system()),
            ("Node Name", platform.node()),
            ("Release", platform.release()),
            ("Version", platform.version()),
            ("Machine", platform.machine()),
            ("Processor", platform.processor()),
            ("CPU Cores", psutil.cpu_count(logical=False)),
            ("Logical CPUs", psutil.cpu_count()),
            ("Total Memory", f"{psutil.virtual_memory().total // (1024**3)} GB"),
            ("Disk Usage", f"{psutil.disk_usage('/').percent}%")
        ]
        
        for i, (label, value) in enumerate(info):
            ttk.Label(sys_info_frame, text=f"{label}:").grid(row=i, column=0, sticky="e", padx=5, pady=2)
            ttk.Label(sys_info_frame, text=value).grid(row=i, column=1, sticky="w", padx=5, pady=2)

    def setup_theme(self):
        """Setup dark/light theme"""
        self.dark_mode = False
        self.style.theme_use("clam")
        
        # Create theme toggle button
        theme_btn = ttk.Button(self.root, text="Toggle Dark Mode", command=self.toggle_theme)
        theme_btn.pack(side="bottom", pady=5)

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.dark_mode = not self.dark_mode
        
        if self.dark_mode:
            self.root.configure(bg="#2d2d2d")
            self.style.configure(".", background="#2d2d2d", foreground="white")
            self.style.configure("TFrame", background="#2d2d2d")
            self.style.configure("TLabel", background="#2d2d2d", foreground="white")
            self.style.configure("Treeview", background="#3d3d3d", foreground="white", fieldbackground="#3d3d3d")
            self.style.configure("Treeview.Heading", background="#4d4d4d", foreground="white")
            self.style.map("Treeview", background=[("selected", "#1d6fa3")])
            plt.style.use("dark_background")
        else:
            self.root.configure(bg="SystemButtonFace")
            self.style.configure(".", background="SystemButtonFace", foreground="black")
            self.style.configure("TFrame", background="SystemButtonFace")
            self.style.configure("TLabel", background="SystemButtonFace", foreground="black")
            self.style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
            self.style.configure("Treeview.Heading", background="SystemButtonFace", foreground="black")
            self.style.map("Treeview", background=[("selected", "#347083")])
            plt.style.use("default")
        
        self.canvas.draw()

    def start_threads(self):
        """Start background threads for monitoring"""
        self.graph_thread = threading.Thread(target=self.update_graph, daemon=True)
        self.graph_thread.start()

    def get_processes(self):
        """Get list of processes with detailed information"""
        process_list = []
        for proc in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent', 'memory_info', 'username', 'nice', 'num_threads']):
            try:
                info = proc.info
                info['username'] = info.get('username', "N/A")
                info['memory_info'] = info['memory_info'].rss // 1024**2 if info['memory_info'] else 0
                info['num_threads'] = info.get('num_threads', 0)
                process_list.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                log_action(f"Process skipped: {e}")
        return process_list

    def update_process_list(self):
        """Update the process list in the UI"""
        if self.paused:
            self.root.after(REFRESH_INTERVAL, self.update_process_list)
            return
        
        try:
            self.tree.delete(*self.tree.get_children())
            processes = self.get_processes()
            
            search_text = self.search_var.get().lower()
            search_by = self.search_by.get().lower()
            
            for process in processes:
                # Apply search filter
                if search_text:
                    if search_by == "name" and search_text not in process['name'].lower():
                        continue
                    elif search_by == "pid" and search_text not in str(process['pid']):
                        continue
                    elif search_by == "user" and search_text not in process['username'].lower():
                        continue
                
                self.tree.insert("", "end", values=(
                    process['pid'], 
                    process['name'], 
                    process['username'], 
                    f"{process['cpu_percent']:.1f}",
                    process['memory_info'], 
                    process['nice'], 
                    process['num_threads']
                ))
            
            self.check_alerts()
            self.status_var.set(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            log_action(f"Error updating process list: {e}")
            self.status_var.set(f"Error: {str(e)}")
        
        self.root.after(REFRESH_INTERVAL, self.update_process_list)

    def debounced_filter(self, event=None):
        """Debounce the filter to avoid rapid updates"""
        if hasattr(self, 'filter_job'):
            self.root.after_cancel(self.filter_job)
        self.filter_job = self.root.after(500, self.update_process_list)

    def kill_process(self):
        """Kill the selected process"""
        selected_item = self.tree.selection()
        if not selected_item:
            self.status_var.set("Warning: Select a process first!")
            return

        pid = self.tree.item(selected_item)['values'][0]
        name = self.tree.item(selected_item)['values'][1]
        
        try:
            process = psutil.Process(pid)
            process.terminate()
            message = f"Process {pid} ({name}) terminated"
            self.status_var.set(message)
            log_action(message)
        except Exception as e:
            message = f"Failed to terminate process {pid}: {e}"
            self.status_var.set(message)
            log_action(message)

    def change_priority(self, value):
        """Change process priority"""
        selected_item = self.tree.selection()
        if not selected_item:
            self.status_var.set("Warning: Select a process first!")
            return

        pid = self.tree.item(selected_item)['values'][0]
        name = self.tree.item(selected_item)['values'][1]
        value = validate_priority(value)
        
        try:
            process = psutil.Process(pid)
            process.nice(value)
            message = f"Process {pid} ({name}) priority changed to {value}"
            self.status_var.set(message)
            log_action(message)
        except Exception as e:
            message = f"Failed to change priority for process {pid}: {e}"
            self.status_var.set(message)
            log_action(message)

    def show_process_details(self):
        """Show detailed information about selected process"""
        selected_item = self.tree.selection()
        if not selected_item:
            self.status_var.set("Warning: Select a process first!")
            return

        pid = self.tree.item(selected_item)['values'][0]
        
        try:
            process = psutil.Process(pid)
            details = f"""
Process Details:
---------------
PID: {pid}
Name: {process.name()}
Status: {process.status()}
CPU %: {process.cpu_percent():.1f}
Memory: {process.memory_info().rss // 1024**2} MB
Threads: {process.num_threads()}
Created: {datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}
User: {process.username()}
"""
            messagebox.showinfo("Process Details", details.strip())
        except Exception as e:
            self.status_var.set(f"Error getting process details: {e}")

    def show_tree_menu(self, event):
        """Show right-click context menu for treeview"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)
    
    def update_graph(self):
        """Update the performance graphs"""
        while self.running:
            if not self.paused:
                try:
                    # Get system metrics
                    cpu = psutil.cpu_percent()
                    mem = psutil.virtual_memory().percent
                    disk = psutil.disk_usage('/').percent
                    net = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
                    
                    # Store data
                    self.cpu_usage.append(cpu)
                    self.mem_usage.append(mem)
                    self.disk_usage.append(disk)
                    self.net_usage.append(net)
                    
                    # Limit data points
                    if len(self.cpu_usage) > GRAPH_DATA_POINTS:
                        self.cpu_usage.pop(0)
                        self.mem_usage.pop(0)
                        self.disk_usage.pop(0)
                        self.net_usage.pop(0)
                    
                    # Update graphs
                    self.ax1.clear()
                    self.ax2.clear()
                    self.ax3.clear()
                    self.ax4.clear()
                    
                    # Store the line objects for hover detection
                    self.ax1.plot(self.cpu_usage, color="red", label="CPU Usage (%)")
                    self.ax2.plot(self.mem_usage, color="blue", label="Memory Usage (%)")
                    self.ax3.plot(self.disk_usage, color="green", label="Disk Usage (%)")
                    self.ax4.plot(self.net_usage, color="purple", label="Network Bytes")
                    
                    for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                        ax.legend(loc="upper right")
                        ax.grid(True, alpha=0.3)
                    
                    self.canvas.draw()
                except Exception as e:
                    log_action(f"Error updating graphs: {e}")
            
            time.sleep(2)

    def check_alerts(self):
        """Check for system alerts"""
        if self.paused or self.alerts_muted:
            return
        
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            if cpu > self.cpu_thresh.get():
                self.status_var.set(f"High CPU Usage: {cpu}% (Threshold: {self.cpu_thresh.get()}%)")
                log_action(f"High CPU alert: {cpu}%")
            
            if mem > self.mem_thresh.get():
                self.status_var.set(f"High Memory Usage: {mem}% (Threshold: {self.mem_thresh.get()}%)")
                log_action(f"High Memory alert: {mem}%")
            
            if disk > ALERT_THRESHOLDS['disk']:
                self.status_var.set(f"High Disk Usage: {disk}% (Threshold: {ALERT_THRESHOLDS['disk']}%)")
                log_action(f"High Disk alert: {disk}%")
        except Exception as e:
            log_action(f"Error checking alerts: {e}")

    def update_thresholds(self):
        """Update alert thresholds"""
        try:
            self.cpu_thresh.set(max(1, min(100, self.cpu_thresh.get())))
            self.mem_thresh.set(max(1, min(100, self.mem_thresh.get())))
            self.status_var.set("Alert thresholds updated")
        except:
            self.status_var.set("Invalid threshold values")

    def toggle_pause(self):
        """Toggle pause state"""
        self.paused = not self.paused
        self.status_var.set("Updates paused" if self.paused else "Resumed updates")

    def toggle_mute_alerts(self):
        """Toggle mute alerts state"""
        self.alerts_muted = not self.alerts_muted
        self.status_var.set("Alerts muted" if self.alerts_muted else "Alerts enabled")

    def export_csv(self):
        """Export process list to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")],
                title="Save Process List"
            )
            
            if filename:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["PID", "Name", "User", "CPU%", "Memory (MB)", "Priority", "Threads"])
                    
                    for item in self.tree.get_children():
                        writer.writerow(self.tree.item(item)['values'])
                
                self.status_var.set(f"Process list exported to {filename}")
                log_action(f"Exported process list to {filename}")
        except Exception as e:
            self.status_var.set(f"Export failed: {e}")
            log_action(f"Export error: {e}")

    def on_close(self):
        """Cleanup on window close"""
        self.running = False
        if hasattr(self, 'graph_thread'):
            self.graph_thread.join(timeout=1)
        self.root.destroy()

# ------------------ Main Application ------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ProcessMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()