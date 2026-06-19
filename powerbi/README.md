# Power BI Dashboard Setup

## Connect to the Data Warehouse

1. Open Power BI Desktop
2. **Get Data** → **SQL Server**
3. Enter your server name and `UK_Road_Traffic_DW` as the database
4. Select **Import** mode
5. Load all 5 tables: `DimDate`, `DimRegion`, `DimLocalAuthority`, `DimCountPoint`, `FactTrafficFlowDirection`

## Verify Relationships

Power BI should auto-detect relationships from the foreign keys. Confirm these exist in **Model View**:

```
FactTrafficFlowDirection.DateKey → DimDate.DateKey
FactTrafficFlowDirection.RegionKey → DimRegion.RegionKey
FactTrafficFlowDirection.LocalAuthorityKey → DimLocalAuthority.LocalAuthorityKey
FactTrafficFlowDirection.CountPointKey → DimCountPoint.CountPointKey
DimLocalAuthority.RegionKey → DimRegion.RegionKey
```

All relationships should be **many-to-one** from Fact to Dimension.

## Suggested Visuals

| Page | Visuals | Fields |
|------|---------|--------|
| **Regional Overview** | Filled map, bar chart | RegionName, TotalMotorVehicles |
| **Trend Analysis** | Line chart | Year (axis), AllMotorVehicles (values) |
| **Road Breakdown** | Stacked bar, table | RoadCategory, vehicle type measures |
| **Traffic Hotspots** | Map (lat/long bubbles) | Latitude, Longitude, AllMotorVehicles (size) |
| **HGV Analysis** | Pie chart, matrix | RegionName, AllHGVs, AllMotorVehicles |

## Key Measures (DAX)

```dax
Total Motor Vehicles = SUM(FactTrafficFlowDirection[AllMotorVehicles])

YoY Growth % =
VAR CurrentYear = SUM(FactTrafficFlowDirection[AllMotorVehicles])
VAR PrevYear = CALCULATE(
    SUM(FactTrafficFlowDirection[AllMotorVehicles]),
    DATEADD(DimDate[FullDate], -1, YEAR)
)
RETURN DIVIDE(CurrentYear - PrevYear, PrevYear, 0)

HGV Percentage = DIVIDE(
    SUM(FactTrafficFlowDirection[AllHGVs]),
    SUM(FactTrafficFlowDirection[AllMotorVehicles]),
    0
)
```

## Geospatial Layer

To add road geometries, import `data/processed/roads_with_traffic_2025.geojson` as a Shape Map data source or use the ArcGIS visual with the lat/long from `DimCountPoint`.
