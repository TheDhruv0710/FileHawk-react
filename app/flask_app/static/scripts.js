// Function to fetch and display task counts on the dashboard
function fetchTaskCounts() {
    fetch('/current_jobs_data')
        .then(response => response.json())
        .then(data => {
            document.getElementById('running-tasks-count').textContent = data.running_jobs;
            document.getElementById('failed-tasks-count').textContent = data.failed_jobs;
            document.getElementById('waiting-tasks-count').textContent = data.waiting_jobs;
            document.getElementById('retrying-tasks-count').textContent = data.retrying_jobs;
        })
        .catch(error => console.error('Error fetching task counts:', error));
}

// Function to fetch and display task execution trends
function fetchTaskTrends() {
    fetch('/task_summary')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('taskTrendChart').getContext('2d');
            const taskTrendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels, // Dates from the API
                    datasets: [{
                        label: 'Tasks Executed',
                        data: data.taskCounts, // Task counts from the API
                        borderColor: 'rgba(75, 192, 192, 1)',
                        fill: false,
                    }]
                },
                options: {
                    responsive: true,
                    animation: {
                        duration: 500,
                    }
                }
            });
        })
        .catch(error => console.error('Error fetching task trends:', error));
}

// Function to fetch and display task statistics
function fetchTaskStatistics(selectedServer) {
    fetch(`/task_summary?server=${selectedServer}`)
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('taskStatisticsChart').getContext('2d');
            const taskStatisticsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels, // Labels from the API
                    datasets: [{
                        label: 'Task Statistics',
                        data: data.statistics, // Statistics data from the API
                        backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    }]
                },
                options: {
                    responsive: true,
                    animation: {
                        duration: 500,
                    }
                }
            });
        })
        .catch(error => console.error('Error fetching task statistics:', error));
}

// Function to fetch and display recent activity
function fetchRecentActivity() {
    fetch('/recent_activity')
        .then(response => response.json())
        .then(data => {
            const timelineContainer = document.getElementById('timelineContainer');
            timelineContainer.innerHTML = ''; // Clear previous content
            data.forEach(activity => {
                const item = document.createElement('div');
                item.className = 'timeline-item';
                item.innerHTML = `<h4>Task ID: ${activity.task_id}</h4><p>Status: ${activity.status}</p><p>Time: ${activity.timestamp}</p>`;
                timelineContainer.appendChild(item);
            });
        })
        .catch(error => console.error('Error fetching recent activity:', error));
}

// Function to delete a task
function deleteTask(taskId) {
    if (confirm("Are you sure you want to delete this task?")) {
        fetch(`/delete_task/${taskId}`, { method: 'DELETE' })
            .then(response => {
                if (response.ok) {
                    document.getElementById(`task-${taskId}`).remove(); // Remove the task row from the table
                } else {
                    console.error('Failed to delete task');
                }
            })
            .catch(error => console.error('Error deleting task:', error));
    }
}

// Event listener for server filter change
document.getElementById('serverFilter').addEventListener('change', function() {
    const selectedServer = this.value;
    fetchTaskStatistics(selectedServer); // Fetch statistics for the selected server
});

// Event listener for apply filters button
document.getElementById("applyFilters").addEventListener("click", function() {
    const timeRange = document.getElementById("timeRange").value;
    const server = document.getElementById("server").value;
    const filePattern = document.getElementById("filePattern").value;

    const url = `/trend_data?time_range=${timeRange}&server=${server}&file_pattern=${filePattern}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('trendChart').getContext('2d');
            const trendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: 'Successes',
                            data: data.successes,
                            borderColor: 'green',
                            backgroundColor: 'rgba(0, 128, 0, 0.2)',
                            fill: true,
                        },
                        {
                            label: 'Failures',
                            data: data.failures,
                            borderColor: 'red',
                            backgroundColor: 'rgba(255, 0, 0, 0.2)',
                            fill: true,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            });
        })
        .catch(error => console.error('Error fetching trend data:', error));
});

// Initialize the dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    fetchTaskCounts(); // Fetch task counts
    fetchTaskTrends(); // Fetch task trends
    fetchRecentActivity(); // Fetch recent activity
});