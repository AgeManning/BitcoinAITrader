-- Build the training set. 

CREATE PROCEDURE TestSet (SuccessTime INT, Percentage INT)
BEGIN

	CREATE TEMPORARY TABLE SuccessTable
	(
		UnixTimeStamp BIGINT,
		Success BOOLEAN
	);

	INSERT INTO
		SucessTable
	SELECT
		rd1.UnixTimeStamp,

		-- Success flag here
	FROM
		RawData rd1
	INNER JOIN
		RawData rd2
	ON
		rd2.UnixTimeStamp BETWEEN rd1.UnixTimeStamp AND rd1.UnixTimeStamp + SucessTime*60*1000*1e6 





END

