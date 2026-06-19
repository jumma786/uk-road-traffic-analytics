USE UK_Road_Traffic_DW;

SELECT 
    r.RegionName,
    SUM(f.AllMotorVehicles) AS TotalMotorVehicles,
    SUM(f.AllHGVs) AS TotalHGVs,
    SUM(f.AllMotorVehicles + f.PedalCycles) AS TotalAllVehicles
FROM FactTrafficFlowDirection f
JOIN DimRegion r ON f.RegionKey = r.RegionKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year = 2023
GROUP BY r.RegionName
ORDER BY TotalAllVehicles DESC;



SELECT TOP 10
    cp.RoadName,
    cp.RoadCategory,
    SUM(f.AllMotorVehicles) AS TotalTraffic,
    AVG(f.AllMotorVehicles) AS AvgDailyFlow
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year >= 2020
GROUP BY cp.RoadName, cp.RoadCategory
HAVING SUM(f.AllMotorVehicles) > 1000000
ORDER BY TotalTraffic DESC;




WITH YearlyTraffic AS (
    SELECT 
        d.Year,
        SUM(f.AllMotorVehicles) AS TotalTraffic
    FROM FactTrafficFlowDirection f
    JOIN DimDate d ON f.DateKey = d.DateKey
    GROUP BY d.Year
)
SELECT 
    Year,
    TotalTraffic,
    LAG(TotalTraffic) OVER (ORDER BY Year) AS PrevYear,
    ROUND(
        (TotalTraffic - LAG(TotalTraffic) OVER (ORDER BY Year)) * 100.0 / 
        NULLIF(LAG(TotalTraffic) OVER (ORDER BY Year), 0), 2
    ) AS YoY_GrowthPct
FROM YearlyTraffic;



SELECT 
    r.RegionName,
    SUM(f.AllHGVs) AS HGV_Total,
    SUM(f.CarsAndTaxis + f.LGVs) AS Passenger_Total,
    ROUND(SUM(f.AllHGVs) * 100.0 / NULLIF(SUM(f.AllMotorVehicles), 0), 2) AS HGV_Pct
FROM FactTrafficFlowDirection f
JOIN DimRegion r ON f.RegionKey = r.RegionKey
GROUP BY r.RegionName
ORDER BY HGV_Pct DESC;




WITH LAGrowth AS (
    SELECT 
        la.LocalAuthorityName,
        d.Year,
        SUM(f.AllMotorVehicles) AS TotalTraffic
    FROM FactTrafficFlowDirection f
    JOIN DimLocalAuthority la ON f.LocalAuthorityKey = la.LocalAuthorityKey
    JOIN DimDate d ON f.DateKey = d.DateKey
    WHERE d.Year IN (2018, 2023)
    GROUP BY la.LocalAuthorityName, d.Year
)
SELECT 
    LocalAuthorityName,
    MAX(CASE WHEN Year = 2023 THEN TotalTraffic END) AS Traffic2023,
    MAX(CASE WHEN Year = 2018 THEN TotalTraffic END) AS Traffic2018,
    ROUND(
        (MAX(CASE WHEN Year = 2023 THEN TotalTraffic END) - 
         MAX(CASE WHEN Year = 2018 THEN TotalTraffic END)) * 100.0 /
        NULLIF(MAX(CASE WHEN Year = 2018 THEN TotalTraffic END), 0), 2
    ) AS GrowthPct
FROM LAGrowth
GROUP BY LocalAuthorityName
HAVING MAX(CASE WHEN Year = 2018 THEN TotalTraffic END) IS NOT NULL
ORDER BY GrowthPct DESC;



SELECT 
    cp.RoadCategory,
    COUNT(DISTINCT cp.CountPointID) AS NumCountPoints,
    SUM(f.AllMotorVehicles) AS TotalTraffic,
    AVG(f.AllMotorVehicles) AS AvgFlowPerPoint
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
GROUP BY cp.RoadCategory
ORDER BY TotalTraffic DESC;




SELECT 
    cp.Latitude,
    cp.Longitude,
    cp.RoadName,
    r.RegionName,
    la.LocalAuthorityName,
    SUM(f.AllMotorVehicles) AS TotalTraffic,
    AVG(f.AllMotorVehicles) AS AvgDailyFlow
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimRegion r ON f.RegionKey = r.RegionKey
JOIN DimLocalAuthority la ON f.LocalAuthorityKey = la.LocalAuthorityKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year = 2023
GROUP BY cp.Latitude, cp.Longitude, cp.RoadName, 
         r.RegionName, la.LocalAuthorityName
HAVING SUM(f.AllMotorVehicles) > 50000
ORDER BY TotalTraffic DESC;