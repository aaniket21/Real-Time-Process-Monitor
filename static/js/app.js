// Initialize WebSocket connection
const socket = io();

// Initialize charts
function createChart(ctx, label, color) {
    const isDarkMode = document.documentElement.classList.contains('dark');
    const textColor = isDarkMode ? '#ffffff' : '#666666';
    const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: color,
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'second',
                        displayFormats: {
                            second: 'HH:mm:ss'
                        }
                    },
                    ticks: {
                        maxTicksLimit: 10,
                        color: textColor
                    },
                    grid: {
                        color: gridColor
                    }
                },
                y: {
                    beginAtZero: true,
                    suggestedMax: label.includes('Network') ? undefined : 100,
                    ticks: {
                        color: textColor,
                        callback: function(value) {
                            if (label.includes('Network')) {
                                return (value / 1024).toFixed(2) + ' KB';
                            }
                            return value + '%';
                        }
                    },
                    grid: {
                        color: gridColor
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: textColor
                    }
                }
            },
            animation: {
                duration: 0
            }
        }
    });
}

const cpuChart = createChart(document.getElementById('cpuChart').getContext('2d'), 'CPU Usage (%)', 'rgb(255, 99, 132)');
const memoryChart = createChart(document.getElementById('memoryChart').getContext('2d'), 'Memory Usage (%)', 'rgb(54, 162, 235)');
const diskChart = createChart(document.getElementById('diskChart').getContext('2d'), 'Disk Usage (%)', 'rgb(75, 192, 192)');
const networkChart = createChart(document.getElementById('networkChart').getContext('2d'), 'Network Bytes', 'rgb(153, 102, 255)');

// Variables for process management
let processes = [];
let filteredProcesses = [];
let selectedPid = null;
let currentSort = { column: null, direction: 1 };
let updatesEnabled = true;
let alertsEnabled = true;
let searchTerm = '';

// Tab switching functionality
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Show selected tab content
    document.getElementById(`${tabName}-tab`).classList.remove('hidden');
    
    // Update tab button styles
    document.querySelectorAll('.tab-button').forEach(button => {
        // Remove all state classes
        button.classList.remove(
            'border-blue-500', 
            'text-blue-600', 
            'dark:text-blue-500', 
            'dark:border-blue-500',
            'text-gray-500',
            'dark:text-gray-400',
            'active-tab'
        );
        // Add inactive state classes
        button.classList.add(
            'border-transparent',
            'text-gray-500',
            'dark:text-gray-400',
            'hover:text-gray-700',
            'hover:border-gray-300',
            'dark:hover:text-gray-300',
            'dark:hover:border-gray-300'
        );
    });
    
    // Highlight active tab
    const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
    // Remove inactive state classes
    activeButton.classList.remove(
        'border-transparent',
        'text-gray-500',
        'dark:text-gray-400',
        'hover:text-gray-700',
        'hover:border-gray-300',
        'dark:hover:text-gray-300',
        'dark:hover:border-gray-300'
    );
    // Add active state classes
    activeButton.classList.add(
        'border-blue-500',
        'text-blue-600',
        'dark:text-blue-500',
        'dark:border-blue-500',
        'active-tab'
    );

    // Resize charts if switching to graphs tab
    if (tabName === 'graphs') {
        [cpuChart, memoryChart, diskChart, networkChart].forEach(chart => {
            chart.resize();
        });
    }
}

// Function to fetch and update processes
async function refreshProcesses() {
    try {
        const response = await axios.get('/processes');  // Remove hardcoded localhost:5000
        processes = response.data;
        
        // Maintain current search filter and sort
        if (searchTerm && searchTerm !== '') {
            filterProcesses(searchTerm);
        } else {
            if (currentSort.column) {
                sortProcesses(processes);
            }
            updateProcessTable(processes);
        }
    } catch (error) {
        console.error('Error fetching processes:', error);
        if (alertsEnabled) {
            alert('Failed to refresh processes. Please try again.');
        }
    }
}

// Function to filter processes
function filterProcesses(term) {
    searchTerm = term.toLowerCase().trim();
    
    if (searchTerm === '') {
        filteredProcesses = [...processes];
        updateProcessTable(filteredProcesses);
        return;
    }
    
    filteredProcesses = processes.filter(process => {
        const searchableValues = [
            process.name?.toLowerCase() || '',
            process.pid?.toString() || '',
            process.user?.toLowerCase() || '',
            process.cpu_percent?.toString() || '',
            process.memory_percent?.toString() || '',
            process.threads?.toString() || '',
            process.start_time?.toLowerCase() || ''
        ];
        
        return searchableValues.some(value => value.includes(searchTerm));
    });
    
    // Maintain current sort if exists
    if (currentSort.column) {
        sortProcesses(filteredProcesses);
    }
    
    updateProcessTable(filteredProcesses);
    
    // Update search input placeholder
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.placeholder = `Found ${filteredProcesses.length} of ${processes.length} processes`;
    }
}

// Function to sort processes
function sortProcesses(processesToSort) {
    return processesToSort.sort((a, b) => {
        let aValue = a[currentSort.column];
        let bValue = b[currentSort.column];

        // Handle numeric values
        if (currentSort.column === 'pid' || 
            currentSort.column === 'cpu_percent' || 
            currentSort.column === 'memory_percent' || 
            currentSort.column === 'threads') {
            aValue = parseFloat(aValue);
            bValue = parseFloat(bValue);
        }

        if (aValue < bValue) return -1 * currentSort.direction;
        if (aValue > bValue) return 1 * currentSort.direction;
        return 0;
    });
}

// Function to sort table
function sortTable(column) {
    if (currentSort.column === column) {
        currentSort.direction *= -1;
    } else {
        currentSort.column = column;
        currentSort.direction = 1;
    }

    // Sort the currently displayed processes (filtered or all)
    const processesToSort = searchTerm ? filteredProcesses : processes;
    sortProcesses(processesToSort);
    updateProcessTable(processesToSort);
}

// Function to update the process table
function updateProcessTable(processesToShow = processes) {
    const tableBody = document.getElementById('processTable');
    if (!tableBody) return;

    tableBody.innerHTML = '';
    
    if (!Array.isArray(processesToShow)) {
        console.error('processesToShow is not an array:', processesToShow);
        return;
    }

    processesToShow.forEach(process => {
        if (!process) return;
        
        const row = document.createElement('tr');
        row.className = 'dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer';
        if (process.pid === selectedPid) {
            row.classList.add('bg-blue-100', 'dark:bg-blue-900');
        }
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">${process.pid || ''}</td>
            <td class="px-6 py-4 whitespace-nowrap">${process.name || ''}</td>
            <td class="px-6 py-4 whitespace-nowrap">${process.cpu_percent?.toFixed(1) || '0'}</td>
            <td class="px-6 py-4 whitespace-nowrap">${process.memory_percent?.toFixed(1) || '0'}</td>
            <td class="px-6 py-4 whitespace-nowrap">${process.user || ''}</td>
            <td class="px-6 py-4 whitespace-nowrap">${process.threads || '0'}</td>
            <td class="px-6 py-4 whitespace-nowrap">${process.start_time || ''}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex space-x-2">
                    <button onclick="showKillModal(${process.pid}); event.stopPropagation();" 
                            class="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700">
                        Kill
                    </button>
                    <button onclick="analyzeProcess(${process.pid}); event.stopPropagation();" 
                            class="px-3 py-1 bg-indigo-500 text-white rounded hover:bg-indigo-600 dark:bg-indigo-600 dark:hover:bg-indigo-700">
                        Analyze
                    </button>
                </div>
            </td>
        `;
        row.addEventListener('click', () => selectProcess(process.pid));
        tableBody.appendChild(row);
    });
}

// Function to select a process
function selectProcess(pid) {
    selectedPid = pid;
    // Highlight selected row
    document.querySelectorAll('#processTable tr').forEach(row => {
        row.classList.remove('bg-blue-100', 'dark:bg-blue-900');
    });
    const selectedRow = Array.from(document.querySelectorAll('#processTable tr')).find(row => 
        row.children[0].textContent === pid.toString()
    );
    if (selectedRow) {
        selectedRow.classList.add('bg-blue-100', 'dark:bg-blue-900');
    }
}

// Process control functions
async function lowerPriority() {
    if (!selectedPid) {
        alert('Please select a process first');
        return;
    }
    try {
        const response = await axios.post('http://localhost:5000/priority', { 
            pid: selectedPid,
            action: 'lower'
        });
        if (alertsEnabled) alert(response.data.message);
    } catch (error) {
        if (alertsEnabled) alert(error.response?.data?.error || 'Error changing priority');
    }
}

async function raisePriority() {
    if (!selectedPid) {
        alert('Please select a process first');
        return;
    }
    try {
        const response = await axios.post('http://localhost:5000/priority', { 
            pid: selectedPid,
            action: 'raise'
        });
        if (alertsEnabled) alert(response.data.message);
    } catch (error) {
        if (alertsEnabled) alert(error.response?.data?.error || 'Error changing priority');
    }
}

function toggleUpdates() {
    updatesEnabled = !updatesEnabled;
    const button = document.querySelector('button[onclick="toggleUpdates()"]');
    if (button) {
        button.textContent = updatesEnabled ? 'Pause Updates' : 'Resume Updates';
        button.classList.toggle('bg-blue-500');
        button.classList.toggle('bg-green-500');
    }
}

function toggleAlerts() {
    alertsEnabled = !alertsEnabled;
    const button = document.querySelector('button[onclick="toggleAlerts()"]');
    if (button) {
        button.textContent = alertsEnabled ? 'Mute Alerts' : 'Unmute Alerts';
        button.classList.toggle('bg-gray-500');
        button.classList.toggle('bg-red-500');
    }
}

// Chart update functions
function updateCharts(data) {
    if (!data) return;
    
    const timestamp = new Date(data.time);
    
    // Update CPU chart
    if (typeof data.cpu === 'number') {
        cpuChart.data.labels.push(timestamp);
        cpuChart.data.datasets[0].data.push(parseFloat(data.cpu.toFixed(1)));
        if (cpuChart.data.labels.length > 60) {
            cpuChart.data.labels.shift();
            cpuChart.data.datasets[0].data.shift();
        }
        cpuChart.update('none');
    }

    // Update Memory chart
    if (typeof data.memory === 'number') {
        memoryChart.data.labels.push(timestamp);
        memoryChart.data.datasets[0].data.push(parseFloat(data.memory.toFixed(1)));
        if (memoryChart.data.labels.length > 60) {
            memoryChart.data.labels.shift();
            memoryChart.data.datasets[0].data.shift();
        }
        memoryChart.update('none');
    }

    // Update Disk chart
    if (typeof data.disk === 'number') {
        diskChart.data.labels.push(timestamp);
        diskChart.data.datasets[0].data.push(parseFloat(data.disk.toFixed(1)));
        if (diskChart.data.labels.length > 60) {
            diskChart.data.labels.shift();
            diskChart.data.datasets[0].data.shift();
        }
        diskChart.update('none');
    }

    // Update Network chart
    if (typeof data.network === 'number') {
        networkChart.data.labels.push(timestamp);
        networkChart.data.datasets[0].data.push(parseFloat((data.network / 1024).toFixed(2)));
        if (networkChart.data.labels.length > 60) {
            networkChart.data.labels.shift();
            networkChart.data.datasets[0].data.shift();
        }
        networkChart.update('none');
    }
}

// Function to export processes to CSV
function exportToCSV() {
    const headers = ['PID', 'Name', 'CPU %', 'Memory %', 'User', 'Threads', 'Start Time'];
    const csvContent = [
        headers.join(','),
        ...processes.map(process => [
            process.pid,
            `"${process.name}"`,
            process.cpu_percent,
            process.memory_percent,
            `"${process.user}"`,
            process.threads,
            `"${process.start_time}"`
        ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `process_snapshot_${new Date().toISOString()}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Function to toggle dark/light theme
function toggleTheme() {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
    } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
    }
    
    // Update chart colors for dark/light mode
    const isDarkMode = document.documentElement.classList.contains('dark');
    const textColor = isDarkMode ? '#ffffff' : '#666666';
    const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Update all charts
    [cpuChart, memoryChart, diskChart, networkChart].forEach(chart => {
        // Update axis colors
        chart.options.scales.x.ticks.color = textColor;
        chart.options.scales.y.ticks.color = textColor;
        chart.options.scales.x.grid.color = gridColor;
        chart.options.scales.y.grid.color = gridColor;
        
        // Update legend colors
        chart.options.plugins.legend.labels.color = textColor;
        
        // Update the chart
        chart.update('none');
    });
}

// Check for saved theme preference
if (localStorage.getItem('theme') === 'dark' || 
    (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
    
    // Set initial chart colors for dark mode
    const textColor = '#ffffff';
    const gridColor = 'rgba(255, 255, 255, 0.1)';
    
    // Update all charts
    [cpuChart, memoryChart, diskChart, networkChart].forEach(chart => {
        // Update axis colors
        chart.options.scales.x.ticks.color = textColor;
        chart.options.scales.y.ticks.color = textColor;
        chart.options.scales.x.grid.color = gridColor;
        chart.options.scales.y.grid.color = gridColor;
        
        // Update legend colors
        chart.options.plugins.legend.labels.color = textColor;
        
        // Update the chart
        chart.update('none');
    });
}

// Function to show kill modal
function showKillModal(pid) {
    selectedPid = pid;
    document.getElementById('killModal').classList.remove('hidden');
}

// Function to close kill modal
function closeKillModal() {
    document.getElementById('killModal').classList.add('hidden');
    selectedPid = null;
}

// Function to confirm and kill process
async function confirmKillProcess() {
    if (!selectedPid) return;

    try {
        const response = await axios.post('http://localhost:5000/kill', { pid: selectedPid });
        alert(response.data.message);
        refreshProcesses();
    } catch (error) {
        alert(error.response?.data?.error || 'Error killing process');
    } finally {
        closeKillModal();
    }
}

// Function to analyze process using AI
async function analyzeProcess(pid) {
    if (!pid) {
        if (alertsEnabled) alert('Please select a process first');
        return;
    }
    
    try {
        // Show loading indicator
        const loadingModal = showLoadingModal('Analyzing process...');
        
        const response = await axios.get(`http://localhost:5000/analyze_process/${pid}`);
        
        // Remove loading indicator
        loadingModal.remove();
        
        // Show analysis results
        showAnalysisModal(response.data);
    } catch (error) {
        if (alertsEnabled) alert(error.response?.data?.error || 'Error analyzing process');
    }
}

// Function to show loading modal
function showLoadingModal(message) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white dark:bg-dark-card p-6 rounded-lg max-w-md w-full">
            <div class="flex items-center justify-center">
                <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
            </div>
            <p class="text-center mt-4 dark:text-white">${message}</p>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

// Function to show analysis modal
function showAnalysisModal(data) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white dark:bg-dark-card p-6 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <h2 class="text-xl font-bold mb-4 dark:text-white">Process Analysis</h2>
            <div class="space-y-4">
                <div>
                    <h3 class="font-semibold dark:text-white">Analysis</h3>
                    <p class="dark:text-gray-300 whitespace-pre-line">${data.analysis}</p>
                </div>
                <div>
                    <h3 class="font-semibold dark:text-white">Anomalies</h3>
                    <p class="dark:text-gray-300 whitespace-pre-line">${data.anomalies}</p>
                </div>
                <div>
                    <h3 class="font-semibold dark:text-white">Recommendations</h3>
                    <p class="dark:text-gray-300 whitespace-pre-line">${data.recommendations}</p>
                </div>
            </div>
            <div class="mt-6 flex justify-end">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                        class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                    Close
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// Function to analyze entire system
async function analyzeSystem() {
    try {
        // Show loading indicator
        const loadingModal = showLoadingModal('Analyzing system...');
        
        const response = await axios.get('http://localhost:5000/analyze_system');
        
        // Remove loading indicator
        loadingModal.remove();
        
        // Show analysis results
        showSystemAnalysisModal(response.data);
    } catch (error) {
        if (alertsEnabled) alert(error.response?.data?.error || 'Error analyzing system');
    }
}

// Function to show system analysis modal
function showSystemAnalysisModal(data) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white dark:bg-dark-card p-6 rounded-lg max-w-4xl w-full max-h-[80vh] overflow-y-auto">
            <h2 class="text-xl font-bold mb-4 dark:text-white">System Analysis</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 class="font-semibold dark:text-white mb-2">Top CPU Processes</h3>
                    <ul class="space-y-1">
                        ${data.system_data.top_cpu_processes.map(p => 
                            `<li class="dark:text-gray-300">${p.name} (${p.cpu_percent}%)</li>`
                        ).join('')}
                    </ul>
                </div>
                <div class="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <h3 class="font-semibold dark:text-white mb-2">Top Memory Processes</h3>
                    <ul class="space-y-1">
                        ${data.system_data.top_memory_processes.map(p => 
                            `<li class="dark:text-gray-300">${p.name} (${p.memory_percent}%)</li>`
                        ).join('')}
                    </ul>
                </div>
            </div>
            
            <div class="space-y-4">
                <div>
                    <h3 class="font-semibold dark:text-white">AI Analysis</h3>
                    <p class="dark:text-gray-300 whitespace-pre-line">${data.analysis}</p>
                </div>
            </div>
            
            <div class="mt-6 flex justify-end">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                        class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                    Close
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    
    if (searchInput) {
        // Clear previous event listeners
        searchInput.replaceWith(searchInput.cloneNode(true));
        const newSearchInput = document.getElementById('searchInput');
        
        // Add input event listener with debounce
        let searchTimeout;
        newSearchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                filterProcesses(e.target.value);
            }, 200); // Reduced debounce delay for better responsiveness
        });

        // Add keydown event listener for immediate clear on Escape
        newSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                newSearchInput.value = '';
                filterProcesses('');
                newSearchInput.blur();
            }
        });
    }

    // Set up WebSocket event listeners
    socket.on('system_stats', (data) => {
        if (updatesEnabled) {
            updateCharts(data);
        }
    });

    // Set up periodic refresh
    let refreshInterval = setInterval(() => {
        if (updatesEnabled) {
            refreshProcesses();
        }
    }, 2000);

    // Initial load
    switchTab('processes');
    refreshProcesses();

    // Add click handler for manual refresh button
    const refreshButton = document.querySelector('button[onclick="refreshProcesses()"]');
    if (refreshButton) {
        refreshButton.addEventListener('click', async (e) => {
            e.preventDefault();
            refreshButton.disabled = true;
            refreshButton.textContent = 'Refreshing...';
            await refreshProcesses();
            refreshButton.textContent = 'Refresh';
            refreshButton.disabled = false;
        });
    }
}); 