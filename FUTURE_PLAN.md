# Future Plan: Series Statistics and Operational Data Management

## Overview
This plan outlines future enhancements for handling operational data characteristics, particularly the dynamic nature of time ranges in operational FEWS systems.

## Operational Data Challenges

### Time Range Dynamics
In operational FEWS systems, time ranges are dynamic:
- **startDate** and **endDate** change daily as new data arrives
- Historical data ranges expand over time
- Forecast data ranges shift forward daily
- Different series may have different update frequencies

### Current Limitation
The current `series_headers` table stores static metadata but doesn't handle dynamic time range information that changes with operational updates.

## Proposed Solution: get_series_statistics Tool

### Purpose
A specialized tool to retrieve current time range statistics for series, providing operational data freshness information.

### Tool Design

#### get_series_statistics.py
- **Input**: `GetSeriesStatisticsInput` with series identifiers
- **Logic**: 
  1. Query webservice for current time range information
  2. Parse XML response for startDate/endDate
  3. Calculate statistics (data coverage, freshness, gaps)
  4. Return operational insights
- **Output**: `GetSeriesStatisticsOutput` with time range statistics

### Data Model

#### GetSeriesStatisticsInput
```python
class GetSeriesStatisticsInput(BaseModel):
    parameter_id: Optional[str] = Field(None, description="Parameter ID to analyze")
    location_id: Optional[str] = Field(None, description="Location ID to analyze")
    series_ids: Optional[List[str]] = Field(None, description="Specific series IDs")
    include_gaps: bool = Field(True, description="Include data gap analysis")
    include_freshness: bool = Field(True, description="Include data freshness metrics")
```

#### GetSeriesStatisticsOutput
```python
class GetSeriesStatisticsOutput(BaseModel):
    series_count: int = Field(..., description="Number of series analyzed")
    summary: str = Field(..., description="Brief operational summary")
    time_ranges: List[SeriesTimeRange] = Field(..., description="Current time ranges")
    freshness_metrics: Optional[FreshnessMetrics] = Field(None, description="Data freshness information")
    gap_analysis: Optional[List[DataGap]] = Field(None, description="Identified data gaps")
    operational_status: str = Field(..., description="Overall operational status")
```

#### SeriesTimeRange
```python
class SeriesTimeRange(BaseModel):
    series_id: str = Field(..., description="Series identifier")
    start_date: datetime = Field(..., description="Current start date")
    end_date: datetime = Field(..., description="Current end date")
    data_points: int = Field(..., description="Number of data points")
    last_update: datetime = Field(..., description="Last data update timestamp")
    update_frequency: str = Field(..., description="Expected update frequency")
```

#### FreshnessMetrics
```python
class FreshnessMetrics(BaseModel):
    oldest_data: datetime = Field(..., description="Oldest data point across series")
    newest_data: datetime = Field(..., description="Newest data point across series")
    average_age_hours: float = Field(..., description="Average data age in hours")
    stale_series_count: int = Field(..., description="Number of series with stale data")
    operational_series_count: int = Field(..., description="Number of series with recent data")
```

### Use Cases

#### 1. Operational Monitoring
```python
# Check data freshness across all Kwel series
stats = get_series_statistics(parameter_id="Kwel")
# Returns: "156 Kwel series analyzed. 142 operational, 14 stale (>24h old)"
```

#### 2. Data Gap Analysis
```python
# Identify series with data gaps
stats = get_series_statistics(location_id="GPG_1698", include_gaps=True)
# Returns: "89 series at GPG_1698. 3 series have gaps in last 7 days"
```

#### 3. Forecast vs Historical Comparison
```python
# Compare historical and forecast data ranges
hist_stats = get_series_statistics(parameter_id="Kwel", module_instance="im.digiflow.model.hist.mswap")
fcst_stats = get_series_statistics(parameter_id="Kwel", module_instance="im.digiflow.model.fcst.mswap")
```

### Implementation Strategy

#### Phase 1: Basic Time Range Retrieval
1. Implement webservice queries for time range information
2. Parse XML responses for startDate/endDate
3. Basic statistics calculation

#### Phase 2: Advanced Analytics
1. Data gap detection algorithms
2. Freshness metrics calculation
3. Operational status classification

#### Phase 3: Integration
1. Integrate with existing series_headers workflow
2. Add operational alerts and notifications
3. Dashboard integration for monitoring

### Benefits

1. **Operational Awareness**: Real-time understanding of data freshness
2. **Quality Assurance**: Identify data gaps and stale series
3. **System Monitoring**: Track operational health of FEWS system
4. **Decision Support**: Help users understand data reliability
5. **Maintenance Planning**: Identify series requiring attention

### Technical Considerations

#### Performance
- Cache time range statistics to avoid frequent webservice calls
- Implement incremental updates for efficiency
- Use batch processing for large series sets

#### Reliability
- Handle webservice timeouts gracefully
- Implement retry logic for failed queries
- Provide fallback to cached statistics

#### Scalability
- Support analysis of large series collections
- Implement parallel processing for multiple series
- Use efficient data structures for gap analysis

## Integration with Current System

### Workflow Enhancement
```
User Request → get_series_headers.py → Check Local Cache → 
├─ If Found: Return from DuckDB
└─ If Not Found: Call ingest_series_headers.py → 
   Fetch from Webservice → Store in DuckDB → Return Results

Additional: get_series_statistics.py → 
   Query Current Time Ranges → Analyze Freshness → Return Operational Insights
```

### Complementary Tools
- `get_series_headers.py`: Static metadata and structure
- `get_series_statistics.py`: Dynamic operational information
- Together: Complete picture of series availability and health

## Future Enhancements

1. **Automated Monitoring**: Scheduled statistics collection and alerting
2. **Trend Analysis**: Historical patterns in data freshness
3. **Predictive Analytics**: Forecast data availability issues
4. **Integration APIs**: Connect with external monitoring systems
5. **Custom Alerts**: User-defined thresholds and notifications
