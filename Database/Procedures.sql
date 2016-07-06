-- MySQL dump 10.13  Distrib 5.5.30, for Linux (x86_64)
--
-- Host: localhost    Database: BitCoins
-- ------------------------------------------------------
-- Server version	5.5.30-log
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping routines for database 'BitCoins'
--
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
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

	
	UPDATE
		RawData rd
	SET
		rd.Time = FROM_UNIXTIME(UnixTimeStamp/1000000)
	WHERE
		rd.UnixTimeStamp = UnixTimeStamp;

	
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
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
		SUM((UnixTimeStamp - @StartingTimeStamp)/1e6/60*(AverageVol/@SumVol)) as Xbar, 			
		SUM(AveragePrice*(AverageVol/@SumVol)) as Ybar, 											
		SUM((UnixTimeStamp - @StartingTimeStamp)/1e6/60*AveragePrice*(AverageVol/@SumVol)) as XYBar, 	
		SUM(POWER((UnixTimeStamp - @StartingTimeStamp)/1e6/60, 2)*(AverageVol/@SumVol)) as X2Bar 	
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

END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE DEFINER=`age`@`localhost` PROCEDURE `IndicatorData`(MinStamp BIGINT, MaxStamp BIGINT)
BEGIN

	-- Create Indicators to be consumed by AI algorithms. 
	-- Version 1.00  - Indicators -  Weighted Linear Gradients
	--							  -  Difference from Weighted Averages

	SELECT
		5min.UnixTimeStamp,
		5min.Value, 
		10min.Value, 
		15min.Value, 
		30min.Value, 
		60min.Value,
		90min.Value,
		rd.AveragePrice - 5ma.Value,
		rd.AveragePrice - 10ma.Value,
		rd.AveragePrice - 15ma.Value,
		rd.AveragePrice - 30ma.Value,
		rd.AveragePrice - 60ma.Value,
		rd.AveragePrice - 90ma.Value
	FROM
		Gradients 5min
	INNER JOIN
		Gradients 10min
	ON
		5min.UnixTimeStamp BETWEEN MinStamp AND MaxStamp AND
		5min.UnixTimeStamp = 10min.UnixTimeStamp AND
		5min.GradientType 	= "5Min" AND
		10min.GradientType = "10Min"
	INNER JOIN
		Gradients 15min
	ON
		15min.UnixTimeStamp = 5min.UnixTimeStamp AND 
		15min.GradientType 	= "15min"
	INNER JOIN
		Gradients 30min
	ON
		30min.UnixTimeStamp = 5min.UnixTimeStamp AND 
		30min.GradientType 	= "30min"
	INNER JOIN
		Gradients 60min
	ON
		60min.UnixTimeStamp = 5min.UnixTimeStamp AND 
		60min.GradientType 	= "60min"
	INNER JOIN
		Gradients 90min 
	ON
		90min.UnixTimeStamp = 5min.UnixTimeStamp AND
		90min.GradientType 	= "90min"
	INNER JOIN
		RawData rd
	ON
		rd.UnixTimeStamp = 5min.UnixTimeStamp
	LEFT JOIN
		MovingAverages 5ma
	ON
		5ma.UnixTimeStamp = 5min.UnixTimeStamp AND
		5ma.Type = "5Min"
	LEFT JOIN
		MovingAverages 10ma
	ON
		10ma.UnixTimeStamp = 5min.UnixTimeStamp AND
		10ma.Type = "10Min"
	LEFT JOIN
		MovingAverages 15ma
	ON
		15ma.UnixTimeStamp = 5min.UnixTimeStamp AND
		15ma.Type = "15Min"
	LEFT JOIN
		MovingAverages 30ma
	ON
		30ma.UnixTimeStamp = 5min.UnixTimeStamp AND
		30ma.Type = "30Min"
	LEFT JOIN
		MovingAverages 60ma
	ON
		60ma.UnixTimeStamp = 5min.UnixTimeStamp AND
		60ma.Type = "60Min"
	LEFT JOIN
		MovingAverages 90ma
	ON
		90ma.UnixTimeStamp = 5min.UnixTimeStamp AND
		90ma.Type = "90Min"
	ORDER BY 
		5min.UnixTimeStamp DESC;

END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
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


END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = '' */ ;
DELIMITER ;;
CREATE DEFINER=`age`@`localhost` PROCEDURE `TestSet`(MinTimeStamp BIGINT, MaxTimeStamp BIGINT, SuccessPeriodMins INT, PercentageChange INT)
BEGIN









		SELECT
			rd1.UnixTimeStamp,
			CASE	WHEN Max(rd2.AveragePrice) > rd1.AveragePrice*(1 + PercentageChange/100) AND MIN(rd2.AveragePrice) > rd1.AveragePrice*(1 - PercentageChange/100) THEN 1
					WHEN MAX(rd2.AveragePrice) < rd1.AveragePrice*(1 + PercentageChange/100) AND MIN(rd2.AveragePrice) < rd2.AveragePrice*(1 - PercentageChange/100) THEN -1
					ELSE 0
			END
		FROM
			RawData rd1
		INNER JOIN
			RawData rd2
		ON
			rd2.UnixTimeStamp BETWEEN rd1.UnixTimeStamp AND rd1.UnixTimeStamp + SuccessPeriodMins*60*1e6
		WHERE
			rd1.UnixTimeStamp BETWEEN MinTimeStamp AND MaxTimeStamp
		GROUP BY
			rd1.UnixTimeStamp
		ORDER BY
			UnixTimeStamp DESC;

		
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2013-05-17 11:56:22
