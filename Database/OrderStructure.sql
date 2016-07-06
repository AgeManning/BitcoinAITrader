-- DB Structure for Ordering

USE BitCoins;

CREATE TABLE IF NOT EXISTS BitCoins.Trades
(
	ID 			INT NOT NULL AUTO_INCREMENT,
	Time			DATETIME NOT NULL,
	Type			VARCHAR(4) NOT NULL,
	Price			DECIMAL(10,5) NOT NULL,
	Amount			DECIMAL(15,8) NOT NULL,
	EffectiveAmount		DECIMAL(15,8) NOT NULL,
	Total			DECIMAL(10,5) NOT NULL,
	EffectiveTotal		DECIMAL(10,5) NOT NULL,
	TradeFee		DECIMAL(4,3) NOT NULL,
	OrderID			VARCHAR(50),
	Partner			INT, -- If Selling, who is its partner. 
	Status			INT NOT NULL, -- 0 Ordered, 1 - Confirmed, 2 - Selling, 3 - Finished, -1 CANCELED
	StatusString		VARCHAR(10) NOT NULL,
	PRIMARY KEY(ID)
);

CREATE TABLE IF NOT EXISTS BitCoins.Funds
(
	TradeID			INT,
	BTCBefore		DECIMAL(15,8),
	BTCAfter		DECIMAL(15,8),
	AUDBefore		DECIMAL(10,5),
	AUDAfter		DECIMAL(10,5),
	PRIMARY KEY(TradeID)
);

CREATE TABLE IF NOT EXISTS BitCoins.TradeSummary
(
	BuyTradeID	INT NOT NULL,
	BuyPrice	DECIMAL(10,5),
	SellPrice	DECIMAL(10,5),
	Amount		DECIMAL(15,8),
	OverallFee	DECIMAL(4,3),
	RawProfit	DECIMAL(10,5),
	ActualProfit 	DECIMAL(10,5)
);

-- Foreign Keys
ALTER TABLE Funds
ADD CONSTRAINT FK_TradeID
FOREIGN KEY (TradeID) REFERENCES Trades(ID)
ON UPDATE CASCADE
ON DELETE CASCADE;
