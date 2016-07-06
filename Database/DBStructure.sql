-- This builds the structure for the database

CREATE TABLE IF NOT EXISTS BitCoins.RawData (
	UnixTimeStamp bigint,
	Time DateTime,
	Price float,
	AveragePrice float,
	AverageVol float,
	DailyVolume float,
	DailyAverage float,
	DailyVolWeightedAverage float,
	primary key (UnixTimeStamp)
);

CREATE Table IF NOT EXISTS BitCoins.MovingAverages
(
	UnixTimeStamp bigint,
	Type VARCHAR(6),
	Value FLOAT,
	PRIMARY KEY (UnixTimeStamp,Type)
);


CREATE TABLE IF NOT EXISTS BitCoins.Gradients
(
	UnixTimeStamp BIGINT,
	GradientType	VARCHAR(10),
	Value			FLOAT,
	PRIMARY KEY (UnixTimeStamp, GradientType)
);	

-- Procedures 

-- --------------------------------------------------------------------------------
-- Routine DDL
-- Note: comments before and after the routine body will not be stored by the server
-- --------------------------------------------------------------------------------

DROP PROCEDURE IF EXISTS Gradients;
DROP PROCEDURE IF EXISTS MovingAverages;
DROP PROCEDURE IF EXISTS CleanAverages;
DELIMITER $$

CREATE DEFINER=`age`@`localhost` PROCEDURE `Gradients`(InputStamp BIGINT, TimePeriod int)
BEGIN

	SET @GradientType = CASE TimePeriod WHEN 1 THEN "1Min" WHEN 5 THEN "5Min" WHEN 10 THEN "10Min" WHEN 15 THEN "15Min" WHEN 30 THEN "30Min" WHEN 60 THEN "60Min" WHEN 90 THEN "90Min" END;
	SET @StartingTimeStamp = InputStamp - TimePeriod*60*1e6;

	CREATE TEMPORARY TABLE 
		GradientData
	AS
	(
		SELECT 
			rd.UnixTimeStamp,
			rd.AveragePrice,
			rd.AverageVol
		FROM
			RawData rd
		WHERE
			rd.UnixTimeStamp >= @StartingTimeStamp AND
			rd.UnixTimeStamp <= InputStamp  
	);

	SELECT
		SUM(AverageVol)
	INTO
		@SumVol
	FROM
		GradientData;


	CREATE TEMPORARY TABLE CalculatedData 
	(
		UnixTimeStamp BIGINT,
		GradientType			VARCHAR(15),
		Xbar					FLOAT,
		YBar					FLOAT,
		XYBar					FLOAT,
		X2Bar					FLOAT
	);
	
	INSERT INTO
		CalculatedData
	SELECT
		InputStamp,
		@GradientType,
		SUM((UnixTimeStamp - @StartingTimeStamp)/1e6/60*(AverageVol/@SumVol)) as Xbar, 			-- X average
		SUM(AveragePrice*(AverageVol/@SumVol)) as Ybar, 											-- Y average
		SUM((UnixTimeStamp - @StartingTimeStamp)/1e6/60*AveragePrice*(AverageVol/@SumVol)) as XYBar, 	-- XY Average
		SUM(POWER((UnixTimeStamp - @StartingTimeStamp)/1e6/60, 2)*(AverageVol/@SumVol)) as X2Bar 	-- X^2 Average
	FROM
		GradientData;

	INSERT INTO
		Gradients(UnixTimeStamp, GradientType, Value)
	SELECT 
		InputStamp,
		@GradientType,
		ifnull((c.XYBar - c.XBar*c.YBar)/(c.X2Bar - POWER(c.Xbar,2)),0) as Value
	FROM 
		CalculatedData c
	LEFT OUTER JOIN
		Gradients g
	ON
		c.UnixTimeStamp = g.UnixTimeStamp AND
		c.GradientType	= g.GradientType
	WHERE
		g.GradientType IS NULL;

	UPDATE
		Gradients g
	INNER JOIN
		CalculatedData c
	ON
		c.UnixTimeStamp 	= g.UnixTimeStamp AND
		c.GradientType		= g.GradientType
	SET
		g.Value = ifnull((c.XYBar - c.XBar*c.YBar)/(c.X2Bar - POWER(c.Xbar,2)),0);

	DROP TABLE CalculatedData;
	DROP TABLE GradientData;	

END

-- --------------------------------------------------------------------------------
-- Routine MovingAverages
-- Note: Calculates the moving averages as the data gets entered
-- --------------------------------------------------------------------------------
DELIMITER $$

CREATE DEFINER=`age`@`localhost` PROCEDURE `MovingAverages`(
	UnixTimeStamp BIGINT,
	TimePeriod INT
)
BEGIN
	
	SET @Type = CASE TimePeriod WHEN 1 THEN "1Min" WHEN 5 THEN "5Min" WHEN 10 THEN "10Min" WHEN 15 THEN "15Min" WHEN 30 THEN "30Min" WHEN 60 THEN "60Min" WHEN 90 THEN "90Min" END;
		
	CREATE TEMPORARY TABLE 
		MovingAverageData
	AS
	(
		SELECT 
			rd.UnixTimeStamp,
			AveragePrice,
			AverageVol
		FROM
			RawData rd
		WHERE
			rd.UnixTimeStamp >= (UnixTimeStamp - TimePeriod*60*1e6) AND
			rd.UnixTimeStamp <= UnixTimeStamp
	);

	CREATE TEMPORARY TABLE CalculatedData 
	(
		UnixTimeStamp BIGINT,
		Type			VARCHAR(6),
		Value			FLOAT
	);

	SELECT
		SUM(AverageVol)
	INTO
		@SumVolume
	FROM
		MovingAverageData;

	IF @SumVolume = 0 THEN
	
		SELECT
			AVG(AveragePrice)
		INTO
			@Value
		FROM
			MovingAverageData;
	
		INSERT INTO
			CalculatedData
		VALUES (UnixTimeStamp, @Type, @Value);

	ELSE
	
		INSERT INTO
			CalculatedData
		SELECT
			UnixTimeStamp,
			@Type as Type,
			SUM(IFNULL(AveragePrice*AverageVol,0))/@SumVolume as Value
		FROM
			MovingAverageData mv
		WHERE
			AverageVol != 0;
	

	END IF;

	INSERT INTO
		MovingAverages(UnixTimeStamp, Type, Value)
	SELECT 
		c.UnixTimeStamp,
		c.Type,
		c.Value
	FROM 
		CalculatedData c
	LEFT OUTER JOIN
		MovingAverages ma
	ON
		c.UnixTimeStamp = ma.UnixTimeStamp AND
		c.Type			= ma.Type
	WHERE
		ma.Type IS NULL;

	UPDATE
		MovingAverages ma
	INNER JOIN
		CalculatedData c
	ON
		c.UnixTimeStamp = ma.UnixTimeStamp AND
		c.Type			= ma.Type
	SET
		ma.Value = c.Value;

	DROP TABLE CalculatedData;
	DROP TABLE MovingAverageData;


END




-- --------------------------------------------------------------------------------
-- Routine CleanAverages
-- Note: Makes sure no doubles get entered and adds the non-unix time to RawData
-- --------------------------------------------------------------------------------
DELIMITER $$

CREATE DEFINER=`age`@`localhost` PROCEDURE `CleanAverages`(UnixTimeStamp BIGINT)
BEGIN

	CREATE TEMPORARY TABLE LastRow (AveragePrice FLOAT, AverageVol FLOAT);

	INSERT INTO
		LastRow
	SELECT
		raw.AveragePrice,
		raw.AverageVol
	FROM
		RawData raw
	WHERE
		raw.UnixTimeStamp = (SELECT Max(rd.UnixTimeStamp) FROM RawData rd WHERE rd.UnixTimeStamp < UnixTimeStamp);

	UPDATE
		RawData rd
	INNER JOIN
		LastRow lr
	ON
		UnixTimeStamp 		= rd.UnixTimeStamp AND
		lr.AveragePrice  	= rd.AveragePrice AND
		lr.AverageVol 	 	= rd.AverageVol
	SET
		rd.AverageVol = 0;

	DROP TABLE LastRow;

	-- Also Update a pretty time. 
	UPDATE
		RawData rd
	SET
		rd.Time = FROM_UNIXTIME(UnixTimeStamp/1000000)
	WHERE
		rd.UnixTimeStamp = UnixTimeStamp;

	
END
