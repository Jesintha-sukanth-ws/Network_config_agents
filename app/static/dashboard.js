/**
 * Network Operations Dashboard JavaScript
 * 
 * Provides real-time visualization of network automation processes.
 * Uses only existing backend data - no automation control capabilities.
 */

class NetworkDashboard {
    constructor() {
        this.refreshInterval = 3000; // 3 seconds
        this.currentTaskSelection = null;
        this.lastUpdate = null;
        
        this.init();
    }
    
    init() {
        console.log('Initializing Network Operations Dashboard...');
        this.hideLoading();
        this.startAutoRefresh();
        this.loadInitialData();
    }
    
    // Data Loading Methods
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadMetrics(),
                this.loadActiveTask(),
                this.loadHistory(),
                this.loadTimeline()
            ]);
            
            this.lastUpdate = new Date();
            this.updateLastUpdateTime();
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('Failed to load dashboard data');
        }
    }
    
    async loadMetrics() {
        try {
            const response = await fetch('/dashboard/api/metrics');
            const metrics = await response.json();
            
            this.updateMetricsDisplay(metrics);
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    }
    
    async loadActiveTask() {
        try {
            const response = await fetch('/dashboard/api/active');
            const data = await response.json();
            
            this.updateActiveTaskDisplay(data.active);
            
            if (data.active) {
                await this.loadPipelineStatus(data.active.sctask);
            } else {
                this.clearPipelineDisplay();
            }
        } catch (error) {
            console.error('Failed to load active task:', error);
        }
    }
    
    async loadHistory() {
        try {
            const response = await fetch('/dashboard/api/history');
            const data = await response.json();
            
            this.updateHistoryDisplay(data.history);
            this.populateTaskSelector(data.history);
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }
    
    async loadTimeline() {
        try {
            const response = await fetch('/dashboard/api/timeline');
            const data = await response.json();
            
            this.updateActivityFeed(data.events);
        } catch (error) {
            console.error('Failed to load timeline:', error);
        }
    }
    
    async loadPipelineStatus(sctask) {
        try {
            const response = await fetch(`/dashboard/api/pipeline/${sctask}`);
            const data = await response.json();
            
            this.updatePipelineDisplay(data);
        } catch (error) {
            console.error('Failed to load pipeline status:', error);
        }
    }
    
    async loadTaskDetails(sctask) {
        try {
            const response = await fetch(`/dashboard/api/history/${sctask}`);
            const data = await response.json();
            
            this.updateTaskDetailsDisplay(data);
        } catch (error) {
            console.error('Failed to load task details:', error);
        }
    }
    
    // Display Update Methods
    updateMetricsDisplay(metrics) {
        document.getElementById('total-tasks').textContent = metrics.total_tasks || 0;
        document.getElementById('success-rate').textContent = `${metrics.success_rate || 0}%`;
        document.getElementById('in-progress').textContent = metrics.in_progress_tasks || 0;
        
        // Update device status
        const deviceCount = Object.keys(metrics.device_breakdown || {}).length;
        document.getElementById('devices-online').textContent = 
            deviceCount > 0 ? `${deviceCount} Devices Online` : 'No Devices';
    }
    
    updateActiveTaskDisplay(activeTask) {
        const container = document.getElementById('active-task-display');
        
        if (!activeTask) {
            container.innerHTML = '<div class="no-active">No active tasks</div>';
            return;
        }
        
        const timeAgo = this.getTimeAgo(activeTask.last_update);
        
        container.innerHTML = `
            <div class="active-task-info">
                <div class="task-header">
                    <strong>${activeTask.sctask}</strong>
                    <span class="task-stage">${activeTask.stage}</span>
                </div>
                <div class="task-description">${activeTask.short_description}</div>
                <div class="task-meta">
                    <span>📋 ${activeTask.cr}</span> • 
                    <span>🔧 ${activeTask.device}</span> • 
                    <span>⏱️ ${timeAgo}</span>
                </div>
            </div>
        `;
    }
    
    updatePipelineDisplay(pipelineData) {
        if (!pipelineData || !pipelineData.pipeline_stages) {
            this.clearPipelineDisplay();
            return;
        }
        
        const stages = [
            { key: 'SCTASK_RECEIVED', name: 'SCTASK Received', icon: '📥' },
            { key: 'CHANGE_REQUEST_CREATED', name: 'Change Request Created', icon: '📋' },
            { key: 'CONFIGURATION_EXECUTING', name: 'Configuration Executing', icon: '⚙️' },
            { key: 'CONFIGURATION_VERIFIED', name: 'Configuration Verified', icon: '✅' },
            { key: 'CHANGE_REQUEST_CLOSED', name: 'Change Request Closed', icon: '🏁' }
        ];
        
        let html = '';
        
        stages.forEach((stage, index) => {
            const stageData = pipelineData.pipeline_stages[stage.key] || {};
            const status = stageData.completed ? 'completed' : 'pending';
            const statusText = stageData.message || (stageData.completed ? 'Completed' : 'Waiting...');
            
            html += `
                <div class="pipeline-stage">
                    <div class="stage-icon">${stage.icon}</div>
                    <div class="stage-info">
                        <div class="stage-name">${stage.name}</div>
                        <div class="stage-status ${status}">${statusText}</div>
                        ${stageData.timestamp ? `<div class="stage-time">${this.formatTime(stageData.timestamp)}</div>` : ''}
                    </div>
                </div>
            `;
            
            if (index < stages.length - 1) {
                html += '<div class="pipeline-connector"></div>';
            }
        });
        
        document.getElementById('pipeline-visualization').innerHTML = html;
    }
    
    clearPipelineDisplay() {
        const stages = [
            { name: 'SCTASK Received', icon: '📥' },
            { name: 'Change Request Created', icon: '📋' },
            { name: 'Configuration Executing', icon: '⚙️' },
            { name: 'Configuration Verified', icon: '✅' },
            { name: 'Change Request Closed', icon: '🏁' }
        ];
        
        let html = '';
        stages.forEach((stage, index) => {
            html += `
                <div class="pipeline-stage">
                    <div class="stage-icon">${stage.icon}</div>
                    <div class="stage-info">
                        <div class="stage-name">${stage.name}</div>
                        <div class="stage-status pending">Waiting...</div>
                    </div>
                </div>
            `;
            
            if (index < stages.length - 1) {
                html += '<div class="pipeline-connector"></div>';
            }
        });
        
        document.getElementById('pipeline-visualization').innerHTML = html;
    }
    
    updateActivityFeed(events) {
        const container = document.getElementById('activity-feed');
        
        if (!events || events.length === 0) {
            container.innerHTML = '<div class="no-activity">No recent activity</div>';
            return;
        }
        
        document.getElementById('activity-count').textContent = events.length;
        
        const recentEvents = events.slice(0, 20); // Show last 20 events
        
        let html = '';
        recentEvents.forEach(event => {
            const timeAgo = this.getTimeAgo(event.timestamp);
            html += `
                <div class="activity-item">
                    <div class="activity-time">${timeAgo}</div>
                    <div class="activity-details">
                        <div class="activity-title severity-${event.severity}">${event.stage}</div>
                        <div class="activity-description">${event.message}</div>
                        <div class="activity-meta">
                            ${event.sctask} • ${event.cr} • ${event.device}
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    updateHistoryDisplay(history) {
        const container = document.getElementById('task-history');
        
        if (!history || history.length === 0) {
            container.innerHTML = '<div class="no-history">No completed tasks</div>';
            return;
        }
        
        document.getElementById('history-count').textContent = `${history.length} tasks`;
        
        let html = '';
        history.forEach(task => {
            const duration = this.calculateDuration(task.started_at, task.completed_at);
            const statusClass = task.status === 'success' ? 'closed' : 'open';
            
            html += `
                <div class="history-item" onclick="selectTask('${task.sctask}')">
                    <div class="history-header">
                        <span class="task-id">${task.sctask}</span>
                        <span class="task-status ${statusClass}">${task.lifecycle_stage}</span>
                    </div>
                    <div class="history-meta">
                        📋 ${task.cr} • 🔧 ${task.device} • ⏱️ ${duration}
                    </div>
                    <div class="history-description">${task.short_description}</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    populateTaskSelector(history) {
        const selector = document.getElementById('task-selector');
        
        // Clear existing options
        selector.innerHTML = '<option value="">Select a task...</option>';
        
        history.forEach(task => {
            const option = document.createElement('option');
            option.value = task.sctask;
            option.textContent = `${task.sctask} - ${task.short_description.substring(0, 50)}...`;
            selector.appendChild(option);
        });
    }
    
    updateTaskDetailsDisplay(taskData) {
        const container = document.getElementById('execution-details');
        
        if (!taskData) {
            container.innerHTML = '<div class="no-selection">Task details not found</div>';
            return;
        }
        
        let html = `
            <div class="details-section">
                <h4>📋 Task Information</h4>
                <div class="task-details">
                    <p><strong>Task:</strong> ${taskData.sctask}</p>
                    <p><strong>Change Request:</strong> ${taskData.cr}</p>
                    <p><strong>Device:</strong> ${taskData.device_data.device_name}</p>
                    <p><strong>Model:</strong> ${taskData.device_data.model}</p>
                    <p><strong>OS:</strong> ${taskData.device_data.os_type}</p>
                </div>
            </div>
        `;
        
        if (taskData.execution_plan && taskData.execution_plan.length > 0) {
            html += `
                <div class="details-section">
                    <h4>⚙️ Execution Plan</h4>
            `;
            
            taskData.execution_plan.forEach((step, index) => {
                html += `
                    <div class="execution-step">
                        <div class="step-header">
                            <span class="step-number">Step ${step.step}</span>
                            <span class="step-operation">${step.intent_type}</span>
                        </div>
                        <div class="step-params">${JSON.stringify(step.parameters, null, 2)}</div>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        if (taskData.stage_history && taskData.stage_history.length > 0) {
            html += `
                <div class="details-section">
                    <h4>📊 Stage History</h4>
            `;
            
            taskData.stage_history.forEach(event => {
                const severityClass = event.status === 'success' ? 'success' : 'info';
                html += `
                    <div class="activity-item">
                        <div class="activity-time">${this.formatTime(event.timestamp)}</div>
                        <div class="activity-details">
                            <div class="activity-title severity-${severityClass}">${event.stage}</div>
                            <div class="activity-description">${event.message}</div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }
        
        container.innerHTML = html;
    }
    
    // Utility Methods
    getTimeAgo(timestamp) {
        if (!timestamp) return 'Unknown';
        
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffDays > 0) return `${diffDays}d ago`;
        if (diffHours > 0) return `${diffHours}h ago`;
        if (diffMins > 0) return `${diffMins}m ago`;
        return 'Just now';
    }
    
    formatTime(timestamp) {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString();
    }
    
    calculateDuration(startTime, endTime) {
        if (!startTime || !endTime) return 'Unknown';
        
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffMins = Math.floor(diffMs / 60000);
        const diffSecs = Math.floor(diffMs / 1000);
        
        if (diffMins > 0) return `${diffMins}m ${diffSecs % 60}s`;
        return `${diffSecs}s`;
    }
    
    updateLastUpdateTime() {
        if (this.lastUpdate) {
            const timeStr = this.lastUpdate.toLocaleTimeString();
            document.getElementById('last-update').textContent = timeStr;
        }
    }
    
    showLoading() {
        document.getElementById('loading-overlay').style.display = 'flex';
    }
    
    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }
    
    showError(message) {
        console.error('Dashboard Error:', message);
        // Could implement toast notifications here
    }
    
    // Auto-refresh functionality
    startAutoRefresh() {
        setInterval(() => {
            this.loadInitialData();
        }, this.refreshInterval);
    }
}

// Global Functions
let dashboard;

function refreshPipeline() {
    if (dashboard) {
        dashboard.loadActiveTask();
    }
}

function selectTask(sctask) {
    document.getElementById('task-selector').value = sctask;
    showTaskDetails();
}

function showTaskDetails() {
    const selector = document.getElementById('task-selector');
    const selectedTask = selector.value;
    
    if (!selectedTask) {
        document.getElementById('execution-details').innerHTML = 
            '<div class="no-selection">Select a task to view details</div>';
        return;
    }
    
    if (dashboard) {
        dashboard.loadTaskDetails(selectedTask);
    }
}

// Initialize Dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    dashboard = new NetworkDashboard();
    
    // Set up task selector change handler
    document.getElementById('task-selector').addEventListener('change', showTaskDetails);
});

// Export for debugging
window.dashboard = dashboard;