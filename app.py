from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psutil
import time
from datetime import datetime
import socketio
import google.generativeai as genai
import os
import requests
import json

app = Flask(__name__)
CORS(app)
sio = socketio.Server(cors_allowed_origins='*')
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyBNbBWGEkJA57LKquLENQFXG9lK--xNjE8"
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Store system metrics history
system_history = {
    'cpu': [],
    'memory': [],
    'disk': [],
    'network': []
}

def get_process_info():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'num_threads', 'create_time']):
        try:
            pinfo = proc.info
            processes.append({
                'pid': pinfo['pid'],
                'name': pinfo['name'],
                'cpu_percent': round(pinfo['cpu_percent'], 1),
                'memory_percent': round(pinfo['memory_percent'], 1),
                'user': pinfo['username'],
                'threads': pinfo['num_threads'],
                'start_time': datetime.fromtimestamp(pinfo['create_time']).strftime('%Y-%m-%d %H:%M:%S')
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/processes', methods=['GET'])
def get_processes():
    return jsonify(get_process_info())

@app.route('/priority', methods=['POST'])
def change_priority():
    data = request.get_json()
    pid = data.get('pid')
    action = data.get('action')
    
    if not pid or not action:
        return jsonify({'error': 'PID and action are required'}), 400
    
    try:
        process = psutil.Process(pid)
        current_nice = process.nice()
        
        if action == 'lower':
            new_nice = min(19, current_nice + 5)
        else:  # raise
            new_nice = max(-20, current_nice - 5)
            
        process.nice(new_nice)
        return jsonify({'message': f'Process {pid} priority changed successfully'})
    except psutil.NoSuchProcess:
        return jsonify({'error': f'No process found with PID {pid}'}), 404
    except psutil.AccessDenied:
        return jsonify({'error': f'Access denied to change priority of process {pid}'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/kill', methods=['POST'])
def kill_process():
    data = request.get_json()
    pid = data.get('pid')
    if not pid:
        return jsonify({'error': 'PID is required'}), 400
    
    try:
        process = psutil.Process(pid)
        process.terminate()
        return jsonify({'message': f'Process {pid} terminated successfully'})
    except psutil.NoSuchProcess:
        return jsonify({'error': f'No process found with PID {pid}'}), 404
    except psutil.AccessDenied:
        return jsonify({'error': f'Access denied to terminate process {pid}'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_system_stats():
    try:
        # Get CPU usage with a small interval for more accurate reading
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get memory information
        memory = psutil.virtual_memory()
        
        # Get disk information for system drive
        try:
            system_drive = os.getenv('SystemDrive', 'C:').rstrip(':')  # Remove colon
            disk = psutil.disk_usage(system_drive + ':\\')  # Use proper Windows path format
        except Exception as disk_error:
            print(f"Error getting disk usage: {str(disk_error)}")
            disk = type('obj', (object,), {'percent': 0.0})
        
        # Get network information
        try:
            network = psutil.net_io_counters()
        except Exception as net_error:
            print(f"Error getting network stats: {str(net_error)}")
            network = type('obj', (object,), {'bytes_sent': 0, 'bytes_recv': 0})
        
        # Get current timestamp in milliseconds
        timestamp = int(time.time() * 1000)
        
        # Create stats object with properly formatted values
        stats = {
            'time': timestamp,
            'cpu': max(0.1, float(cpu_percent)),
            'memory': float(memory.percent),
            'disk': float(disk.percent),
            'network': float(network.bytes_sent + network.bytes_recv)
        }
        
        # Update history with proper data validation
        for metric in ['cpu', 'memory', 'disk', 'network']:
            value = stats[metric]
            if not isinstance(value, (int, float)):
                value = 0.0
            
            system_history[metric].append({
                'time': timestamp,
                'value': value
            })
            
            # Keep only last 60 seconds of data
            current_time = timestamp
            system_history[metric] = [
                entry for entry in system_history[metric] 
                if (current_time - entry['time']) <= 60000
            ]
        
        return stats
    except Exception as e:
        print(f"Error in get_system_stats: {str(e)}")
        # Return default values if there's an error
        return {
            'time': int(time.time() * 1000),
            'cpu': 0.0,
            'memory': 0.0,
            'disk': 0.0,
            'network': 0.0
        }

def update_system_stats():
    while True:
        try:
            stats = get_system_stats()
            # Emit the stats through Socket.IO
            sio.emit('system_stats', stats)
        except Exception as e:
            print(f"Error in update_system_stats: {str(e)}")
        finally:
            # Update every second
            time.sleep(1)

# AI Analysis Functions
def call_gemini_api(prompt):
    """Call Gemini API directly using the REST endpoint"""
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            "contents": [{
                "parts": [{"text": str(prompt)}]
            }]
        }
        
        # Ensure proper JSON encoding of the request
        json_data = json.dumps(data, ensure_ascii=False)
        
        response = requests.post(
            f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}",
            headers=headers,
            json=data  # Use json parameter instead of data for proper JSON encoding
        )
        
        if response.status_code == 200:
            result = response.json()
            # Extract the text from the response
            if 'candidates' in result and len(result['candidates']) > 0:
                if 'content' in result['candidates'][0]:
                    if 'parts' in result['candidates'][0]['content']:
                        if len(result['candidates'][0]['content']['parts']) > 0:
                            if 'text' in result['candidates'][0]['content']['parts'][0]:
                                return result['candidates'][0]['content']['parts'][0]['text']
        
        return f"Error: {response.text}"
    except Exception as e:
        return f"Error calling Gemini API: {str(e)}"

def analyze_process_behavior(process_data):
    """Analyze process behavior using AI"""
    try:
        prompt = f"""
        Analyze this process data and provide insights:
        Process: {process_data['name']}
        CPU Usage: {process_data['cpu_percent']}%
        Memory Usage: {process_data['memory_percent']}%
        Threads: {process_data['threads']}
        Start Time: {process_data['start_time']}
        
        Provide:
        1. Resource usage analysis
        2. Potential performance issues
        3. Recommendations for optimization
        """
        
        return call_gemini_api(prompt)
    except Exception as e:
        return f"Error analyzing process: {str(e)}"

def detect_anomalies(process_data):
    """Detect anomalous process behavior"""
    try:
        prompt = f"""
        Analyze this process for anomalies:
        Process: {process_data['name']}
        CPU Usage: {process_data['cpu_percent']}%
        Memory Usage: {process_data['memory_percent']}%
        Threads: {process_data['threads']}
        
        Identify if this behavior is normal or anomalous.
        """
        
        return call_gemini_api(prompt)
    except Exception as e:
        return f"Error detecting anomalies: {str(e)}"

def get_process_recommendations(process_data):
    """Get AI-powered process management recommendations"""
    try:
        prompt = f"""
        Provide recommendations for this process:
        Process: {process_data['name']}
        CPU Usage: {process_data['cpu_percent']}%
        Memory Usage: {process_data['memory_percent']}%
        Threads: {process_data['threads']}
        
        Suggest:
        1. Priority adjustments
        2. Resource optimization
        3. Potential issues to watch for
        """
        
        return call_gemini_api(prompt)
    except Exception as e:
        return f"Error generating recommendations: {str(e)}"

@app.route('/analyze_process/<int:pid>', methods=['GET'])
def analyze_process(pid):
    try:
        process = psutil.Process(pid)
        process_data = {
            'name': process.name(),
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'threads': process.num_threads(),
            'start_time': datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        analysis = analyze_process_behavior(process_data)
        anomalies = detect_anomalies(process_data)
        recommendations = get_process_recommendations(process_data)
        
        return jsonify({
            'analysis': analysis,
            'anomalies': anomalies,
            'recommendations': recommendations
        })
    except psutil.NoSuchProcess:
        return jsonify({'error': f'No process found with PID {pid}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze_system', methods=['GET'])
def analyze_system():
    try:
        # Get system-wide metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get disk information
        try:
            system_drive = os.getenv('SystemDrive', 'C:').rstrip(':')  # Remove colon
            disk = psutil.disk_usage(system_drive + ':\\')  # Use proper Windows path format
        except Exception as disk_error:
            print(f"Error getting disk usage in analyze_system: {str(disk_error)}")
            disk = type('obj', (object,), {'percent': 0.0})
            
        network = psutil.net_io_counters()
        
        # Get top processes by CPU and memory
        top_cpu_processes = []
        top_memory_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is not None:
                    top_cpu_processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'cpu_percent': round(float(pinfo['cpu_percent']), 1)
                    })
                if pinfo['memory_percent'] is not None:
                    top_memory_processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'memory_percent': round(float(pinfo['memory_percent']), 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, ValueError):
                continue
        
        # Sort by usage
        top_cpu_processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        top_memory_processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        
        # Take top 5
        top_cpu_processes = top_cpu_processes[:5]
        top_memory_processes = top_memory_processes[:5]
        
        # Prepare data for AI analysis
        system_data = {
            'cpu_percent': float(cpu_percent),
            'memory_percent': float(memory.percent),
            'disk_percent': float(disk.percent),
            'network_bytes_sent': int(network.bytes_sent),
            'network_bytes_recv': int(network.bytes_recv),
            'top_cpu_processes': top_cpu_processes,
            'top_memory_processes': top_memory_processes
        }
        
        # Generate AI analysis
        prompt = f"""
        Analyze this system data and provide insights:
        
        System Metrics:
        - CPU Usage: {system_data['cpu_percent']:.1f}%
        - Memory Usage: {system_data['memory_percent']:.1f}%
        - Disk Usage: {system_data['disk_percent']:.1f}%
        - Network: {system_data['network_bytes_sent']} bytes sent, {system_data['network_bytes_recv']} bytes received
        
        Top CPU Processes:
        {', '.join([f"{p['name']} ({p['cpu_percent']:.1f}%)" for p in system_data['top_cpu_processes']])}
        
        Top Memory Processes:
        {', '.join([f"{p['name']} ({p['memory_percent']:.1f}%)" for p in system_data['top_memory_processes']])}
        
        Provide:
        1. Overall system health assessment
        2. Resource usage analysis
        3. Potential performance bottlenecks
        4. Recommendations for optimization
        5. Security considerations
        """
        
        analysis = call_gemini_api(prompt)
        
        return jsonify({
            'analysis': analysis,
            'system_data': system_data
        })
    except Exception as e:
        print(f"Error in analyze_system: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/system_history')
def get_system_history():
    """Endpoint to get system history for initial graph population"""
    return jsonify(system_history)

if __name__ == '__main__':
    import threading
    stats_thread = threading.Thread(target=update_system_stats)
    stats_thread.daemon = True
    stats_thread.start()
    app.run(debug=True, port=5000) 