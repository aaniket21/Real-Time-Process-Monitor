import psutil
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time

#pip install psutil matplotlib
#pip install tk

# ------------------ Fetch Process Details ------------------
def get_processes():
    process_list = []
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent', 'memory_info', 'username', 'nice']):
        try:
            info = proc.info
            info['username'] = info.get('username', "N/A")
            info['memory_info'] = info['memory_info'].rss // 1024**2 if info['memory_info'] else 0
            process_list.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Process skipped: {e}")
    return process_list

# ------------------ Update Process List in UI ------------------
def update_process_list():
    for row in tree.get_children():
        tree.delete(row)  # Clear old data

    processes = get_processes()
    
    for process in processes:
        if filter_var.get() and filter_var.get() != "Filter by Name...":
            if filter_var.get().lower() not in process['name'].lower():
                continue  # Skip non-matching processes
        
        tree.insert("", "end", values=(
            process['pid'], process['name'], process['username'], process['cpu_percent'], 
            process['memory_info'], process['nice']
        ))

    check_cpu_memory_alerts()  # Check alerts
    root.after(3000, update_process_list)  # Refresh every 3 sec

# ------------------ Kill Selected Process ------------------
def kill_process():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Warning", "Select a process first!")
        return

    pid = tree.item(selected_item)['values'][0]
    try:
        process = psutil.Process(pid)
        process.terminate()
        messagebox.showinfo("Success", f"Process {pid} terminated!")
        update_process_list()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to terminate process: {e}")

# ------------------ Change Process Priority ------------------
def change_priority(value):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Warning", "Select a process first!")
        return

    pid = tree.item(selected_item)['values'][0]
    try:
        process = psutil.Process(pid)
        process.nice(value)
        messagebox.showinfo("Success", f"Process {pid} priority changed to {value}!")
        update_process_list()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to change priority: {e}")

# ------------------ Real-Time CPU & Memory Plot ------------------
def update_graph():
    while True:
        cpu_usage.append(psutil.cpu_percent())
        mem_usage.append(psutil.virtual_memory().percent)

        if len(cpu_usage) > 50:
            cpu_usage.pop(0)
            mem_usage.pop(0)

        ax1.clear()
        ax2.clear()

        ax1.plot(cpu_usage, color="red", label="CPU Usage (%)")
        ax2.plot(mem_usage, color="blue", label="Memory Usage (%)")

        ax1.legend(loc="upper right")
        ax2.legend(loc="upper right")

        canvas.draw()
        time.sleep(2)  # Refresh every 2 sec

# ------------------ CPU & Memory Alerts ------------------
def check_cpu_memory_alerts():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent

    if cpu > 80:
        messagebox.showwarning("High CPU Usage!", f"CPU usage is at {cpu}%!")
    if memory > 80:
        messagebox.showwarning("High Memory Usage!", f"Memory usage is at {memory}%!")

# ------------------ GUI Setup ------------------
root = tk.Tk()
root.title("Real-Time Process Monitoring Dashboard")
root.geometry("900x600")

# Process Table
columns = ("PID", "Name", "User", "CPU%", "Memory (MB)", "Priority")
tree = ttk.Treeview(root, columns=columns, show="headings", height=15)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, anchor="center")

tree.pack(fill="x", padx=10, pady=10)

# Filter Entry
filter_var = tk.StringVar()
filter_entry = tk.Entry(root, textvariable=filter_var)
filter_entry.pack(pady=5)
filter_entry.insert(0, "Filter by Name...")
filter_entry.bind("<FocusIn>", lambda event: filter_entry.delete(0, tk.END))

# Buttons
btn_frame = tk.Frame(root)
btn_frame.pack(pady=5)

kill_btn = tk.Button(btn_frame, text="Kill Process", command=kill_process, bg="red", fg="white")
kill_btn.pack(side="left", padx=5)

low_priority_btn = tk.Button(btn_frame, text="Lower Priority", command=lambda: change_priority(19), bg="orange", fg="black")
low_priority_btn.pack(side="left", padx=5)

high_priority_btn = tk.Button(btn_frame, text="Raise Priority", command=lambda: change_priority(-10), bg="green", fg="white")
high_priority_btn.pack(side="left", padx=5)

# Real-Time Graph
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5, 3))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

cpu_usage = []
mem_usage = []

# Start Threads
threading.Thread(target=update_graph, daemon=True).start()
update_process_list()

# Run App
root.mainloop()
