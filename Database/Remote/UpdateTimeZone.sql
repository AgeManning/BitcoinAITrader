

-- UPDATE RawData SET UnixTimeStamp = UnixTimeStamp + 8*3600*1e6;
UPDATE RawData rd SET rd.Time = FROM_UNIXTIME(rd.UnixTimeStamp/1e6);

-- UPDATE Gradients SET UnixTimeStamp = UnixTimeStamp + 8*3600*1e6;

-- UPDATE MovingAverages SET UnixTimeStamp = UnixTimeStamp + 8*3600*1e6;
