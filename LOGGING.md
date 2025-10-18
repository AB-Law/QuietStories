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
# Log level for the application (DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL)
# - DEBUG: Detailed diagnostic information (includes all internal state)
# - VERBOSE: Enhanced logging showing full LLM requests/responses (recommended for troubleshooting)
# - INFO: General application flow (default for production)
# - WARNING: Potential issues and warnings
# - ERROR: Error messages only
# - CRITICAL: Critical failures only
LOG_LEVEL=INFO

# Optional: Custom log file path
LOG_FILE=/path/to/custom.log

# Log retention period in days
LOG_RETENTION_DAYS=7
```

### Logging Levels Explained

QuietStories supports multiple logging levels to help you control the verbosity of logs:

1. **CRITICAL** (50): Only critical failures that require immediate attention
2. **ERROR** (40): Error messages indicating something went wrong
3. **WARNING** (30): Warning messages for potentially problematic situations
4. **INFO** (20): General application flow and status updates (default)
5. **VERBOSE** (15): Enhanced logging with full LLM request/response details
6. **DEBUG** (10): Detailed diagnostic information for debugging

#### When to Use Each Level

- **Production**: Use `INFO` or `WARNING` to keep logs clean while capturing important events
- **Development**: Use `VERBOSE` to see detailed LLM interactions and API calls
- **Debugging**: Use `DEBUG` to see all internal state changes and detailed execution flow
- **Troubleshooting LLM Issues**: Use `VERBOSE` to see complete request/response payloads

#### VERBOSE Level Details

The VERBOSE level (new in this release) provides enhanced logging specifically for LLM provider interactions:

- Shows complete message content sent to LLM providers
- Displays full tool definitions and parameters
- Logs complete response content (not just previews)
- Shows all tool calls with their arguments
- Includes detailed token usage information

Example VERBOSE output:
```
2025-10-18 09:37:23 | INFO | backend.providers.base | [LLM] Call started: gpt-4o-mini
2025-10-18 09:37:23 | VERBOSE | backend.providers.base | [LLM] Full request details for call abc123:
  - Full messages: [{"type": "SystemMessage", "content": "You are a helpful assistant"}, ...]
  - Full tool definitions: [{"name": "get_weather", "description": "...", "args_schema": {...}}]
2025-10-18 09:37:24 | INFO | backend.providers.base | [LLM] Call completed: gpt-4o-mini (850.5ms)
2025-10-18 09:37:24 | VERBOSE | backend.providers.base | [LLM] Full response for call abc123:
  - Full response content: "The weather in San Francisco is..."
  - Full tool calls: [{"id": "call_123", "name": "get_weather", "args": {"location": "SF"}}]
  - Usage details: {"input_tokens": 125, "output_tokens": 75, "total_tokens": 200}
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

# Standard logging levels
logger.info("[Orchestrator] Processing turn 5")
logger.error("Outcome parsing error: validation failed")
logger.warning("[Memory] Cache miss for key: user_123")

# VERBOSE level for detailed LLM interaction logging
logger.verbose("[LLM] Full request payload: {...}")  # type: ignore
logger.debug("[State] Current state: {...}")
```

### Using VERBOSE Logging in Your Code

The VERBOSE level is perfect for logging detailed information about LLM interactions:

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Log detailed API request information
logger.verbose(  # type: ignore
    "Sending request to LLM",
    extra={
        "request_payload": request_data,
        "headers": headers,
        "timeout": timeout_value,
    }
)

# Log full response details
logger.verbose(  # type: ignore
    "Received LLM response",
    extra={
        "response_body": response.json(),
        "status_code": response.status_code,
        "latency_ms": elapsed_time,
    }
)
```

### Custom Log Fields

Add structured data to your logs:

```python
# Components are automatically extracted from [Component] patterns
logger.info("[Parser] Successfully parsed outcome: narrative + 2 state_changes")

# Add contextual information
logger.info(f"[Session] Turn completed: {turn_id}, narrative length: {len(narrative)}")

# Use extra fields for structured data
logger.info(
    "Processing turn",
    extra={
        "turn_id": turn_id,
        "session_id": session_id,
        "user_action": action,
    }
)
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
