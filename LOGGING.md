# QuietStories Centralized Logging

A self-hosted logging solution for QuietStories that provides Datadog-like capabilities using Grafana Loki, Grafana, and Promtail.

## Features

- **🚀 Easy Deployment**: One-command Docker Compose setup
- **📊 Rich Dashboards**: Pre-configured Grafana dashboards for log visualization
- **🔍 Powerful Search**: LogQL queries similar to Datadog's log search
- **🗄️ Configurable Retention**: 1-7 day log retention with automatic cleanup
- **💾 Persistent Storage**: Survives Docker restarts
- **📱 Real-time Monitoring**: Live log streaming and alerts
- **🏷️ Structured Logging**: Automatic parsing of application logs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   QuietStories  │───▶│    Promtail     │───▶│      Loki       │
│   Application   │    │ (Log Shipping)  │    │ (Log Storage)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐                                   │
│     Grafana     │◀──────────────────────────────────┘
│ (Visualization) │
└─────────────────┘
```

## Quick Start

### 1. Start the Logging Stack

```bash
# Start all logging services
./scripts/logging.sh start
```

This will start:
- **Loki** (port 3100): Log aggregation and storage
- **Grafana** (port 3000): Visualization and dashboards
- **Promtail**: Log shipping agent

### 2. Access Grafana Dashboard

Open http://localhost:3001 in your browser:
- **Username**: `admin`
- **Password**: `admin123`

### 3. Start QuietStories

```bash
# Your application will automatically write logs to the logs/ directory
uvicorn backend.main:app --reload
```

## Configuration

### Log Retention

Change log retention period (1-30 days):

```bash
# Set retention to 3 days
./scripts/logging.sh retention 3

# Restart to apply changes
./scripts/logging.sh restart
```

### Environment Variables

Set these in your environment or `.env` file:

```bash
# Log level for the application (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Optional: Custom log file path
LOG_FILE=/path/to/custom.log

# Log retention period in days
LOG_RETENTION_DAYS=7
```

## Management Commands

```bash
# View service status
./scripts/logging.sh status

# View logs from all services
./scripts/logging.sh logs

# View logs from specific service
./scripts/logging.sh logs loki
./scripts/logging.sh logs grafana
./scripts/logging.sh logs promtail

# Stop all services
./scripts/logging.sh stop

# Restart all services
./scripts/logging.sh restart

# Clean up old log files
./scripts/logging.sh cleanup
```

## Dashboard Features

The pre-configured QuietStories dashboard includes:

### 📊 Metrics
- **Log Levels Distribution**: Pie chart showing ERROR, WARNING, INFO counts
- **Log Rate by Level**: Time series of log volume by level
- **Activity by Component**: Track which parts of your app are most active

### 🔍 Log Explorer
- **Real-time Logs**: Live streaming of application logs
- **Structured Parsing**: Automatic extraction of timestamps, levels, and components
- **Search & Filter**: Use LogQL to find specific log entries

### Example Queries

```logql
# Show only ERROR logs
{job="quietstories"} |= "ERROR"

# Show orchestrator component logs
{job="quietstories", component="Orchestrator"}

# Show logs with specific keywords
{job="quietstories"} |= "outcome" |= "parsing"

# Count errors in last hour
count_over_time({job="quietstories", level="ERROR"}[1h])
```

## Integration with Your Code

### Automatic File Logging

The application automatically writes logs to dated files in the `logs/` directory:

```
logs/
├── quietstories-2025-10-14.log
├── quietstories-2025-10-15.log
└── ...
```

### Structured Logging

Use the existing logger in your code:

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# These will appear in Grafana with proper parsing
logger.info("[Orchestrator] Processing turn 5")
logger.error("Outcome parsing error: validation failed")
logger.warning("[Memory] Cache miss for key: user_123")
```

### Custom Log Fields

Add structured data to your logs:

```python
# Components are automatically extracted from [Component] patterns
logger.info("[Parser] Successfully parsed outcome: narrative + 2 state_changes")

# Add contextual information
logger.info(f"[Session] Turn completed: {turn_id}, narrative length: {len(narrative)}")
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# Check service logs
./scripts/logging.sh logs

# Try restarting
./scripts/logging.sh restart
```

### No Logs Appearing

1. Verify application is writing to logs directory:
   ```bash
   ls -la logs/
   ```

2. Check Promtail is reading files:
   ```bash
   ./scripts/logging.sh logs promtail
   ```

3. Verify Loki is receiving logs:
   ```bash
   curl http://localhost:3100/ready
   ```

### Storage Issues

Monitor storage usage:

```bash
# Check Docker volume usage
docker system df

# Clean up old data
./scripts/logging.sh cleanup
```

## Advanced Configuration

### Custom Log Parsing

Edit `logging/promtail-config.yml` to add custom parsing rules:

```yaml
pipeline_stages:
  - regex:
      expression: 'MyCustomPattern: (?P<custom_field>.*)'
  - labels:
      custom_field:
```

### Additional Data Sources

Add more log sources in `logging/promtail-config.yml`:

```yaml
scrape_configs:
  - job_name: nginx
    static_configs:
      - targets: [localhost]
        labels:
          job: nginx
          __path__: /var/log/nginx/*.log
```

### Alerting

Set up alerts in Grafana for critical events:

1. Go to Alerting → Alert Rules in Grafana
2. Create rules based on LogQL queries
3. Configure notification channels (email, Slack, etc.)

## File Structure

```
QuietStories/
├── docker-compose.logging.yml       # Main Docker Compose file
├── scripts/
│   └── logging.sh                   # Management script
├── logging/
│   ├── loki-config.yml             # Loki configuration
│   ├── promtail-config.yml         # Promtail configuration
│   ├── grafana-datasources.yml     # Grafana data sources
│   ├── grafana-dashboards.yml      # Dashboard provisioning
│   └── dashboards/
│       └── quietstories-logs.json  # QuietStories dashboard
└── logs/                            # Application log files
    └── quietstories-YYYY-MM-DD.log
```

## Production Considerations

### Security
- Change default Grafana password
- Restrict network access to logging ports
- Use HTTPS for external access

### Performance
- Monitor disk usage for log storage
- Adjust retention policies based on needs
- Consider log sampling for high-volume applications

### Backup
- Backup Grafana dashboards and configuration
- Consider backing up critical log data

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs: `./scripts/logging.sh logs`
3. Consult [Grafana Loki documentation](https://grafana.com/docs/loki/)
