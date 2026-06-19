-- Single-column indexes on foreign keys
CREATE INDEX IX_Fact_Date ON FactTrafficFlowDirection(DateKey);
CREATE INDEX IX_Fact_Region ON FactTrafficFlowDirection(RegionKey);
CREATE INDEX IX_Fact_LA ON FactTrafficFlowDirection(LocalAuthorityKey);
CREATE INDEX IX_Fact_CP ON FactTrafficFlowDirection(CountPointKey);

-- Composite indexes for common query patterns
CREATE INDEX IX_Fact_Date_Region ON FactTrafficFlowDirection(DateKey, RegionKey)
    INCLUDE (AllMotorVehicles, AllHGVs, PedalCycles);

CREATE INDEX IX_Fact_Date_CP ON FactTrafficFlowDirection(DateKey, CountPointKey)
    INCLUDE (AllMotorVehicles, DirectionOfTravel);

CREATE INDEX IX_Fact_Region_LA ON FactTrafficFlowDirection(RegionKey, LocalAuthorityKey)
    INCLUDE (AllMotorVehicles, AllHGVs);

-- Dimension indexes for join performance
CREATE INDEX IX_CP_RoadCategory ON DimCountPoint(RoadCategory);
CREATE INDEX IX_LA_RegionKey ON DimLocalAuthority(RegionKey);
CREATE INDEX IX_Date_Year ON DimDate(Year);
