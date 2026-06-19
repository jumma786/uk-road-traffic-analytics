USE UK_Road_Traffic_DW;

-- 1. COVID Impact: 2019 vs 2020 vs 2021 recovery by vehicle type
SELECT
    d.Year,
    SUM(f.CarsAndTaxis) AS Cars,
    SUM(f.BusesAndCoaches) AS Buses,
    SUM(f.LGVs) AS LGVs,
    SUM(f.AllHGVs) AS HGVs,
    SUM(f.PedalCycles) AS Cycles,
    SUM(f.AllMotorVehicles) AS AllMotor
FROM FactTrafficFlowDirection f
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year BETWEEN 2019 AND 2023
GROUP BY d.Year
ORDER BY d.Year;


-- 2. COVID Impact by Region: which regions recovered fastest
WITH RegionYearly AS (
    SELECT
        r.RegionName,
        d.Year,
        SUM(f.AllMotorVehicles) AS Traffic
    FROM FactTrafficFlowDirection f
    JOIN DimRegion r ON f.RegionKey = r.RegionKey
    JOIN DimDate d ON f.DateKey = d.DateKey
    WHERE d.Year IN (2019, 2020, 2023)
    GROUP BY r.RegionName, d.Year
)
SELECT
    RegionName,
    MAX(CASE WHEN Year = 2019 THEN Traffic END) AS Traffic_2019,
    MAX(CASE WHEN Year = 2020 THEN Traffic END) AS Traffic_2020,
    MAX(CASE WHEN Year = 2023 THEN Traffic END) AS Traffic_2023,
    ROUND(
        (MAX(CASE WHEN Year = 2020 THEN Traffic END) -
         MAX(CASE WHEN Year = 2019 THEN Traffic END)) * 100.0 /
        NULLIF(MAX(CASE WHEN Year = 2019 THEN Traffic END), 0), 2
    ) AS Covid_Drop_Pct,
    ROUND(
        (MAX(CASE WHEN Year = 2023 THEN Traffic END) -
         MAX(CASE WHEN Year = 2019 THEN Traffic END)) * 100.0 /
        NULLIF(MAX(CASE WHEN Year = 2019 THEN Traffic END), 0), 2
    ) AS Recovery_Pct
FROM RegionYearly
GROUP BY RegionName
ORDER BY Covid_Drop_Pct;


-- 3. Cycling Trends: pedal cycle growth over time
SELECT
    d.Year,
    SUM(f.PedalCycles) AS TotalCycles,
    COUNT(DISTINCT f.CountPointKey) AS CountPointsWithCycles,
    AVG(CASE WHEN f.PedalCycles > 0 THEN f.PedalCycles END) AS AvgCyclesWherePresent
FROM FactTrafficFlowDirection f
JOIN DimDate d ON f.DateKey = d.DateKey
GROUP BY d.Year
ORDER BY d.Year;


-- 4. Cycling vs Motor Vehicle Modal Shift
WITH Yearly AS (
    SELECT
        d.Year,
        SUM(f.PedalCycles) AS Cycles,
        SUM(f.AllMotorVehicles) AS Motor
    FROM FactTrafficFlowDirection f
    JOIN DimDate d ON f.DateKey = d.DateKey
    GROUP BY d.Year
)
SELECT
    Year,
    Cycles,
    Motor,
    ROUND(Cycles * 100.0 / NULLIF(Motor + Cycles, 0), 4) AS Cycle_Share_Pct,
    LAG(Cycles) OVER (ORDER BY Year) AS PrevCycles,
    ROUND(
        (Cycles - LAG(Cycles) OVER (ORDER BY Year)) * 100.0 /
        NULLIF(LAG(Cycles) OVER (ORDER BY Year), 0), 2
    ) AS Cycle_YoY_Pct
FROM Yearly
ORDER BY Year;


-- 5. Directional Imbalance: find commuter corridors
SELECT
    cp.RoadName,
    cp.RoadCategory,
    r.RegionName,
    f.DirectionOfTravel,
    SUM(f.AllMotorVehicles) AS DirectionalFlow
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimRegion r ON f.RegionKey = r.RegionKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year = 2023
    AND f.DirectionOfTravel != 'C'
GROUP BY cp.RoadName, cp.RoadCategory, r.RegionName, f.DirectionOfTravel
HAVING SUM(f.AllMotorVehicles) > 10000
ORDER BY cp.RoadName, f.DirectionOfTravel;


-- 6. Vehicle-Kilometres by Region (AADF * link_length)
SELECT
    r.RegionName,
    d.Year,
    SUM(CAST(f.AllMotorVehicles AS FLOAT) * cp.LinkLengthKm * 365) AS VehicleKm_Annual,
    SUM(CAST(f.AllHGVs AS FLOAT) * cp.LinkLengthKm * 365) AS HGV_VehicleKm_Annual
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimRegion r ON f.RegionKey = r.RegionKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year >= 2019
GROUP BY r.RegionName, d.Year
ORDER BY r.RegionName, d.Year;


-- 7. Road Category Performance Over Time
SELECT
    cp.RoadCategory,
    d.Year,
    COUNT(DISTINCT cp.CountPointID) AS NumPoints,
    SUM(f.AllMotorVehicles) AS TotalFlow,
    AVG(f.AllMotorVehicles) AS AvgFlow,
    SUM(f.AllHGVs) AS TotalHGV,
    ROUND(SUM(f.AllHGVs) * 100.0 / NULLIF(SUM(f.AllMotorVehicles), 0), 2) AS HGV_Pct
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year >= 2015
GROUP BY cp.RoadCategory, d.Year
ORDER BY cp.RoadCategory, d.Year;


-- 8. Top Growing and Declining Roads (2019 vs 2023)
WITH RoadTraffic AS (
    SELECT
        cp.RoadName,
        cp.RoadCategory,
        d.Year,
        SUM(f.AllMotorVehicles) AS Traffic
    FROM FactTrafficFlowDirection f
    JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
    JOIN DimDate d ON f.DateKey = d.DateKey
    WHERE d.Year IN (2019, 2023)
    GROUP BY cp.RoadName, cp.RoadCategory, d.Year
)
SELECT TOP 20
    RoadName,
    RoadCategory,
    MAX(CASE WHEN Year = 2019 THEN Traffic END) AS Traffic_2019,
    MAX(CASE WHEN Year = 2023 THEN Traffic END) AS Traffic_2023,
    ROUND(
        (MAX(CASE WHEN Year = 2023 THEN Traffic END) -
         MAX(CASE WHEN Year = 2019 THEN Traffic END)) * 100.0 /
        NULLIF(MAX(CASE WHEN Year = 2019 THEN Traffic END), 0), 2
    ) AS Change_Pct
FROM RoadTraffic
GROUP BY RoadName, RoadCategory
HAVING MAX(CASE WHEN Year = 2019 THEN Traffic END) > 100000
ORDER BY Change_Pct DESC;


-- 9. LGV Growth Trend (e-commerce indicator)
SELECT
    d.Year,
    SUM(f.LGVs) AS TotalLGVs,
    SUM(f.AllMotorVehicles) AS TotalMotor,
    ROUND(SUM(f.LGVs) * 100.0 / NULLIF(SUM(f.AllMotorVehicles), 0), 2) AS LGV_Share_Pct
FROM FactTrafficFlowDirection f
JOIN DimDate d ON f.DateKey = d.DateKey
GROUP BY d.Year
ORDER BY d.Year;


-- 10. Congestion Proxy: traffic density per km of road
SELECT TOP 20
    cp.RoadName,
    cp.RoadCategory,
    r.RegionName,
    cp.LinkLengthKm,
    SUM(f.AllMotorVehicles) AS TotalFlow,
    ROUND(SUM(f.AllMotorVehicles) / NULLIF(cp.LinkLengthKm, 0), 0) AS FlowPerKm
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimRegion r ON f.RegionKey = r.RegionKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year = 2023 AND cp.LinkLengthKm > 0
GROUP BY cp.RoadName, cp.RoadCategory, r.RegionName, cp.LinkLengthKm
HAVING SUM(f.AllMotorVehicles) > 10000
ORDER BY FlowPerKm DESC;


-- 11. Motorway vs A-road: comparative trends
SELECT
    d.Year,
    SUM(CASE WHEN cp.RoadCategory IN ('TM', 'PM') THEN f.AllMotorVehicles ELSE 0 END) AS Motorway_Flow,
    SUM(CASE WHEN cp.RoadCategory IN ('TA', 'PA') THEN f.AllMotorVehicles ELSE 0 END) AS ARoad_Flow,
    SUM(CASE WHEN cp.RoadCategory IN ('M', 'MB', 'MCU') THEN f.AllMotorVehicles ELSE 0 END) AS Minor_Flow,
    COUNT(DISTINCT CASE WHEN cp.RoadCategory IN ('TM', 'PM') THEN cp.CountPointID END) AS Motorway_Points,
    COUNT(DISTINCT CASE WHEN cp.RoadCategory IN ('TA', 'PA') THEN cp.CountPointID END) AS ARoad_Points
FROM FactTrafficFlowDirection f
JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
JOIN DimDate d ON f.DateKey = d.DateKey
GROUP BY d.Year
ORDER BY d.Year;


-- 12. HGV Axle Breakdown Over Time
SELECT
    d.Year,
    SUM(f.HGVs2RigidAxle) AS Rigid2,
    SUM(f.HGVs3RigidAxle) AS Rigid3,
    SUM(f.HGVs4OrMoreRigidAxle) AS Rigid4Plus,
    SUM(f.HGVs3Or4ArticulatedAxle) AS Artic3_4,
    SUM(f.HGVs5ArticulatedAxle) AS Artic5,
    SUM(f.HGVs6ArticulatedAxle) AS Artic6,
    SUM(f.AllHGVs) AS TotalHGV,
    ROUND(SUM(f.HGVs5ArticulatedAxle + f.HGVs6ArticulatedAxle) * 100.0 /
        NULLIF(SUM(f.AllHGVs), 0), 2) AS LargeArtic_Pct
FROM FactTrafficFlowDirection f
JOIN DimDate d ON f.DateKey = d.DateKey
GROUP BY d.Year
ORDER BY d.Year;


-- 13. Bus & Coach Decline
SELECT
    d.Year,
    SUM(f.BusesAndCoaches) AS TotalBuses,
    SUM(f.AllMotorVehicles) AS TotalMotor,
    ROUND(SUM(f.BusesAndCoaches) * 100.0 /
        NULLIF(SUM(f.AllMotorVehicles), 0), 3) AS Bus_SharePct
FROM FactTrafficFlowDirection f
JOIN DimDate d ON f.DateKey = d.DateKey
GROUP BY d.Year
ORDER BY d.Year;


-- 14. Motorcycle/Scooter Trends (delivery economy)
SELECT
    d.Year,
    SUM(f.TwoWheeledMotorVehicles) AS TotalMotorcycles,
    SUM(f.AllMotorVehicles) AS TotalMotor,
    ROUND(SUM(f.TwoWheeledMotorVehicles) * 100.0 /
        NULLIF(SUM(f.AllMotorVehicles), 0), 3) AS Motorcycle_SharePct
FROM FactTrafficFlowDirection f
JOIN DimDate d ON f.DateKey = d.DateKey
GROUP BY d.Year
ORDER BY d.Year;


-- 15. Count Point Coverage by Region and Road Type
SELECT
    r.RegionName,
    cp.RoadCategory,
    COUNT(DISTINCT cp.CountPointID) AS NumPoints,
    SUM(cp.LinkLengthKm) AS TotalLinkKm,
    ROUND(COUNT(DISTINCT cp.CountPointID) * 1.0 /
        NULLIF(SUM(cp.LinkLengthKm), 0) * 100, 2) AS PointsPer100km
FROM DimCountPoint cp
JOIN FactTrafficFlowDirection f ON f.CountPointKey = cp.CountPointKey
JOIN DimRegion r ON f.RegionKey = r.RegionKey
JOIN DimDate d ON f.DateKey = d.DateKey
WHERE d.Year = 2023
GROUP BY r.RegionName, cp.RoadCategory
ORDER BY r.RegionName, cp.RoadCategory;


-- 16. Directional Imbalance: top commuter corridors
WITH DirFlow AS (
    SELECT
        cp.RoadName,
        cp.RoadCategory,
        r.RegionName,
        f.DirectionOfTravel,
        SUM(f.AllMotorVehicles) AS Flow
    FROM FactTrafficFlowDirection f
    JOIN DimCountPoint cp ON f.CountPointKey = cp.CountPointKey
    JOIN DimRegion r ON f.RegionKey = r.RegionKey
    JOIN DimDate d ON f.DateKey = d.DateKey
    WHERE d.Year = 2023 AND f.DirectionOfTravel != 'C'
    GROUP BY cp.RoadName, cp.RoadCategory, r.RegionName, f.DirectionOfTravel
),
DirPivot AS (
    SELECT
        RoadName, RoadCategory, RegionName,
        MAX(Flow) AS MaxDirFlow,
        MIN(Flow) AS MinDirFlow
    FROM DirFlow
    GROUP BY RoadName, RoadCategory, RegionName
    HAVING COUNT(*) >= 2
)
SELECT TOP 30
    RoadName, RoadCategory, RegionName,
    MaxDirFlow, MinDirFlow,
    ROUND(CAST(MaxDirFlow AS FLOAT) / NULLIF(MinDirFlow, 0), 2) AS ImbalanceRatio
FROM DirPivot
WHERE MinDirFlow > 1000
ORDER BY ImbalanceRatio DESC;
