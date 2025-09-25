#!/bin/bash
# Production Monitoring Setup Script for Clean Timestamp Implementation
# Automates deployment and configuration of timestamp health monitoring

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
MONITORING_DIR="${SCRIPT_DIR}"
LOG_DIR="${PROJECT_ROOT}/logs"
VENV_DIR="${PROJECT_ROOT}/agenthub_main/.venv"

# Monitoring configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Display header
show_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║        Timestamp Health Monitoring Setup      ║"
    echo "║           Production Deployment v1.0          ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "${YELLOW}API Endpoint: ${API_BASE_URL}${RESET}"
    echo -e "${YELLOW}Check Interval: ${CHECK_INTERVAL} seconds${RESET}"
    echo -e "${YELLOW}Data Retention: ${RETENTION_DAYS} days${RESET}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${RESET}"

    local has_errors=false

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is not installed${RESET}"
        has_errors=true
    else
        echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${RESET}"
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
        echo -e "${RED}❌ pip is not available${RESET}"
        has_errors=true
    else
        echo -e "${GREEN}✅ pip available${RESET}"
    fi

    # Check virtual environment
    if [[ -d "$VENV_DIR" ]]; then
        echo -e "${GREEN}✅ Virtual environment found: ${VENV_DIR}${RESET}"
    else
        echo -e "${YELLOW}⚠️ Virtual environment not found, will create one${RESET}"
    fi

    # Check monitoring directory structure
    if [[ ! -d "$MONITORING_DIR" ]]; then
        echo -e "${RED}❌ Monitoring directory not found: ${MONITORING_DIR}${RESET}"
        has_errors=true
    else
        echo -e "${GREEN}✅ Monitoring directory exists${RESET}"
    fi

    # Check for monitoring script
    if [[ ! -f "${MONITORING_DIR}/timestamp_health_monitor.py" ]]; then
        echo -e "${RED}❌ Health monitor script not found${RESET}"
        has_errors=true
    else
        echo -e "${GREEN}✅ Health monitor script found${RESET}"
    fi

    if [[ "$has_errors" == "true" ]]; then
        echo -e "${RED}❌ Prerequisites check failed. Please fix the issues above.${RESET}"
        exit 1
    fi

    echo -e "${GREEN}✅ All prerequisites satisfied${RESET}"
}

# Setup Python environment
setup_python_environment() {
    echo -e "${BLUE}🐍 Setting up Python environment...${RESET}"

    # Create virtual environment if it doesn't exist
    if [[ ! -d "$VENV_DIR" ]]; then
        echo -e "${YELLOW}Creating Python virtual environment...${RESET}"
        python3 -m venv "$VENV_DIR"
    fi

    # Activate virtual environment
    source "${VENV_DIR}/bin/activate"

    # Upgrade pip
    echo -e "${YELLOW}Upgrading pip...${RESET}"
    pip install --upgrade pip

    # Install monitoring dependencies
    echo -e "${YELLOW}Installing monitoring dependencies...${RESET}"
    pip install aiohttp psutil pyyaml sqlite3

    # Install additional production dependencies
    pip install prometheus-client flask requests

    echo -e "${GREEN}✅ Python environment ready${RESET}"
}

# Setup monitoring directories
setup_directories() {
    echo -e "${BLUE}📁 Setting up monitoring directories...${RESET}"

    # Create log directory
    mkdir -p "$LOG_DIR"
    echo -e "${GREEN}✅ Log directory: ${LOG_DIR}${RESET}"

    # Create monitoring data directory
    mkdir -p "${MONITORING_DIR}/data"
    echo -e "${GREEN}✅ Data directory: ${MONITORING_DIR}/data${RESET}"

    # Create backup directory
    mkdir -p "${MONITORING_DIR}/backups"
    echo -e "${GREEN}✅ Backup directory: ${MONITORING_DIR}/backups${RESET}"

    # Create alerts directory
    mkdir -p "${MONITORING_DIR}/alerts"
    echo -e "${GREEN}✅ Alerts directory: ${MONITORING_DIR}/alerts${RESET}"

    # Set permissions
    chmod 755 "${MONITORING_DIR}/timestamp_health_monitor.py"

    echo -e "${GREEN}✅ Directory structure ready${RESET}"
}

# Configure monitoring service
configure_monitoring() {
    echo -e "${BLUE}⚙️ Configuring monitoring service...${RESET}"

    # Create systemd service file (if running as root/sudo)
    if [[ $EUID -eq 0 ]]; then
        cat > /etc/systemd/system/timestamp-monitor.service << EOF
[Unit]
Description=Timestamp Health Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
User=$(logname)
Group=$(logname)
WorkingDirectory=${MONITORING_DIR}
Environment=PATH=${VENV_DIR}/bin
ExecStart=${VENV_DIR}/bin/python timestamp_health_monitor.py --api-url ${API_BASE_URL} --interval ${CHECK_INTERVAL} --retention-days ${RETENTION_DAYS} --log-level ${LOG_LEVEL}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd and enable service
        systemctl daemon-reload
        systemctl enable timestamp-monitor.service

        echo -e "${GREEN}✅ Systemd service configured${RESET}"
    else
        echo -e "${YELLOW}⚠️ Not running as root, systemd service not created${RESET}"
        echo -e "${YELLOW}To run as service, re-run with sudo or use manual startup${RESET}"
    fi

    # Create startup script
    cat > "${MONITORING_DIR}/start_monitoring.sh" << EOF
#!/bin/bash
# Start timestamp health monitoring
cd "${MONITORING_DIR}"
source "${VENV_DIR}/bin/activate"

echo "🚀 Starting timestamp health monitoring..."
echo "API URL: ${API_BASE_URL}"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Log level: ${LOG_LEVEL}"
echo "Press Ctrl+C to stop"
echo ""

python timestamp_health_monitor.py \\
    --api-url "${API_BASE_URL}" \\
    --interval ${CHECK_INTERVAL} \\
    --retention-days ${RETENTION_DAYS} \\
    --log-level ${LOG_LEVEL}
EOF

    chmod +x "${MONITORING_DIR}/start_monitoring.sh"

    # Create stop script
    cat > "${MONITORING_DIR}/stop_monitoring.sh" << EOF
#!/bin/bash
# Stop timestamp health monitoring
echo "🛑 Stopping timestamp health monitoring..."

# Stop systemd service if running
if systemctl is-active --quiet timestamp-monitor.service; then
    sudo systemctl stop timestamp-monitor.service
    echo "✅ Systemd service stopped"
fi

# Kill any running monitor processes
pkill -f "timestamp_health_monitor.py" || true
echo "✅ Monitor processes stopped"
EOF

    chmod +x "${MONITORING_DIR}/stop_monitoring.sh"

    echo -e "${GREEN}✅ Monitoring service configured${RESET}"
}

# Test monitoring setup
test_monitoring() {
    echo -e "${BLUE}🧪 Testing monitoring setup...${RESET}"

    # Activate virtual environment
    source "${VENV_DIR}/bin/activate"

    # Change to monitoring directory
    cd "$MONITORING_DIR"

    # Test API connectivity
    echo -e "${YELLOW}Testing API connectivity...${RESET}"
    if curl -s -f "${API_BASE_URL}/health" > /dev/null; then
        echo -e "${GREEN}✅ API is accessible${RESET}"
    else
        echo -e "${RED}❌ API is not accessible: ${API_BASE_URL}${RESET}"
        echo -e "${YELLOW}Please ensure the application is running${RESET}"
    fi

    # Run health check (dry run)
    echo -e "${YELLOW}Running initial health check...${RESET}"
    timeout 30 python timestamp_health_monitor.py \
        --api-url "${API_BASE_URL}" \
        --interval 5 \
        --log-level DEBUG \
        2>&1 | head -20 || true

    echo -e "${GREEN}✅ Initial health check completed${RESET}"
}

# Display monitoring commands
show_monitoring_commands() {
    echo -e "${CYAN}📚 Monitoring Commands:${RESET}"
    echo ""
    echo -e "${GREEN}Start Monitoring (Manual):${RESET}"
    echo "  cd ${MONITORING_DIR}"
    echo "  ./start_monitoring.sh"
    echo ""
    echo -e "${GREEN}Stop Monitoring:${RESET}"
    echo "  ./stop_monitoring.sh"
    echo ""
    if [[ $EUID -eq 0 ]]; then
        echo -e "${GREEN}Start as System Service:${RESET}"
        echo "  sudo systemctl start timestamp-monitor.service"
        echo ""
        echo -e "${GREEN}Check Service Status:${RESET}"
        echo "  sudo systemctl status timestamp-monitor.service"
        echo ""
        echo -e "${GREEN}View Service Logs:${RESET}"
        echo "  sudo journalctl -u timestamp-monitor.service -f"
        echo ""
    fi
    echo -e "${GREEN}View Monitoring Logs:${RESET}"
    echo "  tail -f ${MONITORING_DIR}/timestamp_monitor.log"
    echo ""
    echo -e "${GREEN}View Health Data:${RESET}"
    echo "  sqlite3 ${MONITORING_DIR}/monitoring_data.db"
    echo "  SELECT * FROM health_reports ORDER BY timestamp DESC LIMIT 10;"
    echo ""
    echo -e "${GREEN}Configuration File:${RESET}"
    echo "  ${MONITORING_DIR}/monitoring_config.yml"
    echo ""
}

# Create monitoring dashboard script
create_dashboard() {
    echo -e "${BLUE}📊 Creating monitoring dashboard...${RESET}"

    cat > "${MONITORING_DIR}/dashboard.py" << 'EOF'
#!/usr/bin/env python3
"""
Simple web dashboard for timestamp health monitoring
"""

import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path(__file__).parent / "monitoring_data.db"

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Timestamp Health Monitor</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .status { padding: 15px; border-radius: 8px; margin: 10px 0; }
        .healthy { background-color: #d4edda; border-left: 4px solid #28a745; }
        .degraded { background-color: #fff3cd; border-left: 4px solid #ffc107; }
        .critical { background-color: #f8d7da; border-left: 4px solid #dc3545; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #333; }
        .metric-unit { font-size: 0.8em; color: #666; }
        .alert { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 10px; margin: 5px 0; border-radius: 5px; }
        .timestamp { font-size: 0.9em; color: #666; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .refresh-info { text-align: center; color: #666; font-size: 0.9em; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 Timestamp Health Monitor</h1>
        <p>Real-time monitoring of clean timestamp implementation</p>
        <div class="timestamp">Last updated: {{ current_time }}</div>
    </div>

    <div class="status {{ status_class }}">
        <h2>Overall Status: {{ overall_status }}</h2>
        {% if alerts %}
            <h3>Active Alerts:</h3>
            {% for alert in alerts %}
                <div class="alert">{{ alert }}</div>
            {% endfor %}
        {% endif %}
    </div>

    <div class="metrics">
        {% for metric in key_metrics %}
        <div class="metric-card">
            <h3>{{ metric.name|replace('_', ' ')|title }}</h3>
            <div class="metric-value">
                {{ "%.2f"|format(metric.value) }}
                <span class="metric-unit">{{ metric.unit }}</span>
            </div>
            <div class="timestamp">{{ metric.timestamp }}</div>
            {% if metric.details %}
                <div class="metric-details">{{ metric.details }}</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <h3>Recent Health Reports</h3>
    <table>
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>Status</th>
                <th>Alerts</th>
                <th>Key Metrics</th>
            </tr>
        </thead>
        <tbody>
            {% for report in recent_reports %}
            <tr>
                <td>{{ report.timestamp }}</td>
                <td class="{{ report.status_class }}">{{ report.overall_status }}</td>
                <td>{{ report.alert_count }}</td>
                <td>{{ report.metric_summary }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="refresh-info">
        🔄 Page refreshes automatically every 30 seconds
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard view"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Get latest health report
            cursor = conn.execute("""
                SELECT timestamp, overall_status, metrics_json, alerts_json
                FROM health_reports
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            latest_report = cursor.fetchone()

            if not latest_report:
                return "No monitoring data available"

            timestamp, overall_status, metrics_json, alerts_json = latest_report
            metrics = json.loads(metrics_json)
            alerts = json.loads(alerts_json)

            # Get recent reports
            cursor = conn.execute("""
                SELECT timestamp, overall_status, alerts_json, metrics_json
                FROM health_reports
                ORDER BY timestamp DESC
                LIMIT 10
            """)

            recent_reports = []
            for row in cursor.fetchall():
                alerts_data = json.loads(row[2])
                metrics_data = json.loads(row[3])

                recent_reports.append({
                    'timestamp': row[0],
                    'overall_status': row[1],
                    'status_class': row[1].lower(),
                    'alert_count': len(alerts_data),
                    'metric_summary': f"{len(metrics_data)} metrics"
                })

            # Key metrics to highlight
            key_metric_names = [
                'api_response_time',
                'timestamp_task_creation_avg',
                'timestamp_task_update_avg',
                'system_cpu_utilization',
                'system_memory_utilization'
            ]

            key_metrics = [
                metric for metric in metrics
                if metric['name'] in key_metric_names
            ]

            return render_template_string(
                DASHBOARD_HTML,
                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                overall_status=overall_status.upper(),
                status_class=overall_status.lower(),
                alerts=alerts,
                key_metrics=key_metrics,
                recent_reports=recent_reports
            )

    except Exception as e:
        return f"Dashboard error: {str(e)}"

@app.route('/api/health')
def api_health():
    """API endpoint for health data"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT timestamp, overall_status, metrics_json, alerts_json
                FROM health_reports
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            result = cursor.fetchone()

            if not result:
                return jsonify({'error': 'No data available'})

            return jsonify({
                'timestamp': result[0],
                'overall_status': result[1],
                'metrics': json.loads(result[2]),
                'alerts': json.loads(result[3])
            })

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    print("🚀 Starting monitoring dashboard on http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)
EOF

    chmod +x "${MONITORING_DIR}/dashboard.py"

    # Create dashboard startup script
    cat > "${MONITORING_DIR}/start_dashboard.sh" << EOF
#!/bin/bash
cd "${MONITORING_DIR}"
source "${VENV_DIR}/bin/activate"

echo "🚀 Starting monitoring dashboard on http://localhost:8080"
python dashboard.py
EOF

    chmod +x "${MONITORING_DIR}/start_dashboard.sh"

    echo -e "${GREEN}✅ Monitoring dashboard created${RESET}"
    echo -e "${CYAN}Access dashboard at: http://localhost:8080${RESET}"
}

# Main setup function
main() {
    show_header

    echo -e "${YELLOW}🚀 Starting timestamp health monitoring setup...${RESET}"
    echo ""

    # Run setup steps
    check_prerequisites
    echo ""

    setup_python_environment
    echo ""

    setup_directories
    echo ""

    configure_monitoring
    echo ""

    create_dashboard
    echo ""

    test_monitoring
    echo ""

    echo -e "${GREEN}✅ Monitoring setup completed successfully!${RESET}"
    echo ""

    show_monitoring_commands

    # Ask if user wants to start monitoring now
    echo -e "${YELLOW}Would you like to start monitoring now? (y/N)${RESET}"
    read -r start_now

    if [[ "$start_now" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}🚀 Starting monitoring...${RESET}"
        cd "$MONITORING_DIR"
        ./start_monitoring.sh
    else
        echo -e "${CYAN}💡 To start monitoring later, run:${RESET}"
        echo "  cd ${MONITORING_DIR} && ./start_monitoring.sh"
    fi
}

# Run main function
main "$@"
EOF

chmod +x "${MONITORING_DIR}/setup_monitoring.sh"