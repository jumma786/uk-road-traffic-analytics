USE UK_Road_Traffic_DW;
GO

CREATE TABLE DimDate (
    DateKey INT PRIMARY KEY,
    FullDate DATE NOT NULL,
    Year INT,
    Quarter INT,
    Month INT,
    MonthName NVARCHAR(10),
    Day INT,
    DayOfWeek INT,
    DayName NVARCHAR(10),
    IsWeekend BIT,
    FiscalYear INT
);

CREATE TABLE DimRegion (
    RegionKey INT IDENTITY(1,1) PRIMARY KEY,
    RegionID INT NOT NULL,
    RegionName NVARCHAR(100),
    RegionONSCode NVARCHAR(10)
);

CREATE TABLE DimLocalAuthority (
    LocalAuthorityKey INT IDENTITY(1,1) PRIMARY KEY,
    LocalAuthorityID INT NOT NULL,
    RegionKey INT FOREIGN KEY REFERENCES DimRegion(RegionKey),
    LocalAuthorityName NVARCHAR(100),
    LocalAuthorityCode NVARCHAR(10)
);

CREATE TABLE DimCountPoint (
    CountPointKey INT IDENTITY(1,1) PRIMARY KEY,
    CountPointID INT NOT NULL,
    RoadName NVARCHAR(50),
    RoadCategory NVARCHAR(20),
    RoadType NVARCHAR(20),
    Latitude DECIMAL(10, 8),
    Longitude DECIMAL(11, 8),
    LinkLengthKm DECIMAL(8, 3)
);

CREATE TABLE FactTrafficFlowDirection (
    TrafficFlowKey BIGINT IDENTITY(1,1) PRIMARY KEY,
    DateKey INT FOREIGN KEY REFERENCES DimDate(DateKey),
    CountPointKey INT FOREIGN KEY REFERENCES DimCountPoint(CountPointKey),
    LocalAuthorityKey INT FOREIGN KEY REFERENCES DimLocalAuthority(LocalAuthorityKey),
    RegionKey INT FOREIGN KEY REFERENCES DimRegion(RegionKey),
    DirectionOfTravel NVARCHAR(10),
    PedalCycles DECIMAL(18,2),
    TwoWheeledMotorVehicles DECIMAL(18,2),
    CarsAndTaxis DECIMAL(18,2),
    BusesAndCoaches DECIMAL(18,2),
    LGVs DECIMAL(18,2),
    HGVs2RigidAxle DECIMAL(18,2),
    HGVs3RigidAxle DECIMAL(18,2),
    HGVs4OrMoreRigidAxle DECIMAL(18,2),
    HGVs3Or4ArticulatedAxle DECIMAL(18,2),
    HGVs5ArticulatedAxle DECIMAL(18,2),
    HGVs6ArticulatedAxle DECIMAL(18,2),
    AllHGVs DECIMAL(18,2),
    AllMotorVehicles DECIMAL(18,2),
    LoadDate DATETIME DEFAULT GETDATE()
);




USE UK_Road_Traffic_DW;

SELECT 
    TABLE_NAME,
    TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;


USE UK_Road_Traffic_DW;

-- Clear all dimension tables (safe, they have no foreign key constraints yet)
TRUNCATE TABLE DimDate;
TRUNCATE TABLE DimRegion;
TRUNCATE TABLE DimLocalAuthority;
TRUNCATE TABLE DimCountPoint;

USE UK_Road_Traffic_DW;

SELECT 'DimDate' as TableName, COUNT(*) as TotalRows FROM DimDate
UNION ALL
SELECT 'DimRegion', COUNT(*) FROM DimRegion
UNION ALL
SELECT 'DimLocalAuthority', COUNT(*) FROM DimLocalAuthority
UNION ALL
SELECT 'DimCountPoint', COUNT(*) FROM DimCountPoint;



USE UK_Road_Traffic_DW;

SELECT 
    'DimDate' as TableName, 
    COUNT(*) as TotalRows 
FROM DimDate
UNION ALL
SELECT 'DimRegion', COUNT(*) FROM DimRegion
UNION ALL
SELECT 'DimLocalAuthority', COUNT(*) FROM DimLocalAuthority
UNION ALL
SELECT 'DimCountPoint', COUNT(*) FROM DimCountPoint
UNION ALL
SELECT 'FactTrafficFlowDirection', COUNT(*) FROM FactTrafficFlowDirection;