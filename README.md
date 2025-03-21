﻿
# **Real-Time Process Monitor**

## 📌 Project Overview
The **Real-Time Process Monitor** is a Python-based desktop application designed to **track and manage system processes** with an intuitive graphical user interface (GUI). This project enables users to **monitor CPU and memory usage** in real time, terminate processes, and adjust their priority levels efficiently. It also features **dynamic performance graphs** and alerts for high resource usage, making it a valuable tool for system management.

---

## 🚀 Key Features
✅ **Real-Time Process Monitoring:** Displays a list of active processes with essential details such as PID, name, user, CPU, and memory usage.  
✅ **Process Management:** Allows terminating processes and modifying their priority to optimize system performance.  
✅ **Dynamic Performance Graphs:** Live charts for CPU and memory usage, providing visual insights into system resource consumption.  
✅ **Search and Filter:** Easily locate specific processes by filtering through the process list.  
✅ **Performance Alerts:** Automatically triggers warnings when CPU or memory usage exceeds **80%**, helping to prevent potential system slowdowns.  

---

## 🛠️ Technologies Used
- **Python 3.x** – Programming language used for core functionality.  
- **Tkinter** – GUI library for creating the interactive desktop interface.  
- **psutil** – Library for retrieving information on system processes and resource usage.  
- **matplotlib** – Library for rendering real-time performance graphs.  

---

## 📥 Installation Guide

### **Step 1: Clone the Repository**
To get started, clone this repository to your local machine using the following command:
```bash
git clone https://github.com/yourusername/Real-Time-Process-Monitor.git
cd Real-Time-Process-Monitor
```

### **Step 2: Install Dependencies**
Ensure you have Python installed. Then, install the required libraries by running:
```bash
pip install psutil matplotlib
```

---

## ▶️ Running the Application

Execute the following command to start the application:
```bash
python process_monitor.py
```

### **How to Use**
- 📊 **Process List:** View and filter running processes by name.  
- ⚙️ **Manage Processes:** Select a process to terminate it or change its priority.  
- 📈 **Performance Graphs:** Monitor CPU and memory usage through dynamic visualizations.  
- ⚠️ **Alerts:** Receive warnings for high resource consumption.  

---

## 🎯 Application Workflow

### **1. Real-Time Process Tracking**
The program continuously retrieves process information and refreshes the display every **3 seconds**. It captures the following details:  
- **Process ID (PID)**  
- **Process Name**  
- **User Running the Process**  
- **CPU Usage (%)**  
- **Memory Consumption (MB)**  
- **Priority Level**  

### **2. Process Management**
You can interact with processes using the following options:  
- 🔴 **Kill Process:** Terminate unwanted or problematic processes.  
- 🔼 **Increase Priority:** Boost priority for essential processes.  
- 🔽 **Decrease Priority:** Lower priority for non-critical processes.  

### **3. Graphical Performance Monitoring**
- **CPU Usage Graph:** Displays real-time CPU load trends.  
- **Memory Usage Graph:** Shows dynamic memory consumption patterns.  

---

## ⚠️ Alert System
The application includes a **performance alert system** that triggers warnings when:  
- **CPU usage** exceeds **80%**.  
- **Memory usage** surpasses **80%**.  

These alerts help you proactively manage system resources and prevent potential slowdowns.  

---

## 📷 Screenshots
![image](https://github.com/user-attachments/assets/3b2aec79-dff4-4ef5-9a7f-e1e2a0df44b8)


---

## 🤝 Contributing
Contributions are welcome! If you have suggestions or improvements, feel free to open an issue or submit a pull request.

