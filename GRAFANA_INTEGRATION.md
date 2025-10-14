# Dashboard Integration Guide

## Viewing Logs in Grafana

### 1. Initial Access
- Open http://localhost:3001
- Login with:
  - Username: `admin`
  - Password: `admin123`

### 2. QuietStories Dashboard
The pre-built dashboard is automatically available:
1. Go to **Dashboards** → **Browse**
2. Click on **QuietStories Logs**

### 3. Dashboard Panels Explained

#### **Log Levels Pie Chart**
- Shows distribution of ERROR, WARNING, INFO logs
- Helps identify if your app has too many errors
- Query: `sum by (level) (count_over_time({job="quietstories"}[5m]))`

#### **Log Rate Timeline**
- Real-time chart showing log volume by severity
- Spikes indicate high activity or issues
- Query: `sum by (level) (rate({job="quietstories"}[1m]))`

#### **Component Activity**
- Shows which parts of your app are most active
- Tracks [Orchestrator], [Parser], [Memory], etc.
- Query: `sum by (component) (rate({job="quietstories", component!=""}[1m]))`

#### **Live Log Stream**
- Real-time log viewer at the bottom
- Full-text search and filtering
- Click on log lines to see details

## Using the Log Explorer

### 1. Access Log Explorer
- Click **Explore** in the left sidebar
- Select **Loki** as the data source

### 2. Basic Queries

```logql
# All QuietStories logs
{job="quietstories"}

# Only errors
{job="quietstories"} |= "ERROR"

# Specific component
{job="quietstories", component="Orchestrator"}

# Search for keywords
{job="quietstories"} |= "outcome" |= "parsing"

# Time range with errors
{job="quietstories", level="ERROR"} [1h]
```

### 3. Advanced Filtering

```logql
# Multiple components
{job="quietstories"} | json | component =~ "Orchestrator|Parser"

# Exclude debug logs
{job="quietstories"} != "DEBUG"

# Find validation errors
{job="quietstories"} |= "validation" |= "error"

# Session-specific logs
{job="quietstories"} |= "session_id" |= "your-session-id"
```

### 4. Metric Queries

```logql
# Count errors per minute
sum(rate({job="quietstories", level="ERROR"}[1m]))

# Top error components
topk(5, sum by (component) (count_over_time({job="quietstories", level="ERROR"}[1h])))

# Log volume over time
sum(rate({job="quietstories"}[5m]))
```

## Dashboard Customization

### 1. Adding New Panels

1. Open your dashboard
2. Click **Add** → **Add Panel**
3. Choose panel type:
   - **Time series**: For metrics over time
   - **Logs**: For log viewing
   - **Stat**: For single values
   - **Table**: For structured data

### 2. Custom Log Panels

#### Error Rate Panel
```logql
# Query
sum(rate({job="quietstories", level="ERROR"}[5m]))

# Panel Settings
- Type: Stat
- Title: "Error Rate"
- Unit: "requests/sec"
- Thresholds: Green < 0.1, Red > 1
```

#### Recent Errors Panel
```logql
# Query
{job="quietstories", level="ERROR"}

# Panel Settings
- Type: Logs
- Title: "Recent Errors"
- Max lines: 100
- Show time: Yes
```

#### Component Health Panel
```logql
# Query
sum by (component) (rate({job="quietstories"}[5m])) > 0

# Panel Settings
- Type: Table
- Title: "Active Components"
- Show: Component name and request rate
```

### 3. Creating Alerts

1. Go to **Alerting** → **Alert Rules**
2. Click **New Rule**
3. Example: High Error Rate Alert

```logql
# Query A
sum(rate({job="quietstories", level="ERROR"}[5m]))

# Condition
IS ABOVE 0.5

# Evaluation
Every: 1m
For: 2m

# Annotations
Summary: High error rate detected in QuietStories
Description: Error rate is {{ $value }} errors/sec
```

## Integration with Your Application

### 1. Structured Logging for Better Dashboards

Update your code to use consistent log formats:

```python
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Good: Structured logging
logger.info("[Orchestrator] Turn completed", extra={
    "turn_id": turn_id,
    "session_id": session_id,
    "duration_ms": duration,
    "narrative_length": len(narrative)
})

# Good: Component tagging
logger.error("[Parser] Validation failed", extra={
    "error_type": "validation",
    "field": "state_changes",
    "input_data": data_preview
})
```

### 2. Custom Metrics

Add custom log-based metrics:

```python
# Performance tracking
logger.info(f"[Performance] Turn processing time: {duration_ms}ms", extra={
    "metric": "turn_duration",
    "value": duration_ms,
    "session_id": session_id
})

# Business metrics
logger.info(f"[Business] Story generated", extra={
    "metric": "story_generated",
    "narrative_length": len(narrative),
    "turns_count": turns,
    "user_id": user_id
})
```

### 3. Dashboard Variables

Create dynamic dashboards with variables:

1. Dashboard Settings → Variables → Add Variable
2. **Name**: `session_id`
3. **Type**: Query
4. **Query**: `label_values({job="quietstories"}, session_id)`

Use in panels: `{job="quietstories", session_id="$session_id"}`

## Advanced Log Analysis

### 1. Log Aggregation

```logql
# Average response times (if logged)
avg_over_time({job="quietstories"} | regexp "duration: (?P<duration>\\d+)ms" | unwrap duration [5m])

# Error patterns
sum by (error_type) (count_over_time({job="quietstories"} | json | error_type != "" [1h]))

# User activity
sum by (user_id) (count_over_time({job="quietstories"} | json | user_id != "" [1h]))
```

### 2. Correlation Analysis

```logql
# Find errors around specific times
{job="quietstories", level="ERROR"} and on()
{job="quietstories"} |= "session_id" |= "problem-session"

# Memory usage correlation
{job="quietstories"} |= "memory" and
{job="quietstories", level="ERROR"}
```

### 3. Performance Analysis

```logql
# Slow operations
{job="quietstories"} |= "slow" or
{job="quietstories"} | regexp "duration: [5-9]\\d\\d\\dms|duration: \\d{5,}ms"

# High activity periods
rate({job="quietstories"}[1m]) > 2
```

## Best Practices

### 1. Dashboard Organization
- Group related panels together
- Use consistent time ranges
- Add descriptions to panels
- Use meaningful titles

### 2. Query Optimization
- Use specific labels when possible
- Limit time ranges for expensive queries
- Use stream selectors before line filters
- Cache frequently used queries

### 3. Alerting Strategy
- Alert on error rates, not individual errors
- Use appropriate thresholds
- Include context in alert messages
- Test alerts with dummy data

### 4. Log Management
- Use structured logging consistently
- Include correlation IDs (session_id, request_id)
- Log at appropriate levels
- Include relevant context

## Troubleshooting Common Issues

### No Logs Appearing
1. Check if application is running: `./scripts/logging.sh logs promtail`
2. Verify log files exist: `ls -la logs/`
3. Check Loki ingestion: `curl http://localhost:3100/ready`

### Query Too Slow
1. Add more specific labels: `{job="quietstories", level="ERROR"}`
2. Reduce time range
3. Use line filters early: `{job="quietstories"} |= "error"`

### Missing Labels
1. Update Promtail config to extract more labels
2. Restart promtail: `./scripts/logging.sh restart`
3. Check log format matches regex patterns

## Example Dashboards

### Operations Dashboard
- Error rate trend
- Log volume by component
- Recent critical errors
- System health indicators

### Development Dashboard
- Debug log stream
- Component activity
- Performance metrics
- Feature usage tracking

### Business Dashboard
- User activity metrics
- Story generation stats
- Feature adoption rates
- Error impact analysis
