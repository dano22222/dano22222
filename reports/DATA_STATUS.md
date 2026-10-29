# Completed NO3 weather experiment

The required NO3/2024 regional experiment is complete. The analysis uses the 1000-point regional mean, not the pilot.

| Check | Result |
|---|---|
| Sampled locations | 1000 |
| UTC hours per location | 8784 |
| Point-hours | 8,784,000 |
| Temperature and precipitation values | 17,568,000 |
| Missing values in regional mean | 0 |
| Returned ERA5 grid cells represented | 222 |
| Maximum difference after independent mean recomputation | 0.0 |

The hourly API quota was reached after 957 successful locations. All successful point files were preserved and the remaining 43 were fetched in the next permitted hourly window. No endpoint switching, paid account or quota bypass was used.

Spatial means use equal weights for the uniformly sampled locations. Locations sharing a model grid cell are spatially dependent; API temperature values may also be elevation adjusted. See weather_audit.json and ASSUMPTIONS.md for the detailed record. Bulk point caches remain available locally and are excluded from Git; the completed mean and provenance are included in the repository.
