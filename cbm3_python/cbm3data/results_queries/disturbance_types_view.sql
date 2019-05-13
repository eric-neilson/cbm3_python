SELECT
tblDisturbanceType.DistTypeID,
tblDisturbanceType.DefaultDistTypeID,
tblDisturbanceType.DistTypeName,
tblDisturbanceTypeDefault.DistTypeName
FROM tblDisturbanceType 
INNER JOIN tblDisturbanceTypeDefault ON 
tblDisturbanceType.DefaultDistTypeID = tblDisturbanceTypeDefault.DistTypeID;