## Functions and Variables for the Trader Class ##
## Converted to a class to store an instance of BTCInstance ## <- This maintains ExchangeRates and uses less memory

## Still need to account for Transaction Fees... Not sure how MtGox does it yet.
## Find out in Beta Run
import datetime
from datetime import timedelta


## Ultra Import Function. Logic must be perfect!
def CheckOrders(Trader):
    ## In AccountInfo There is ['Wallets']['BTC']['Open_Orders'] - May be handy
    ## Have GetOrderInfo()a
    ## Check before and after status update to make sure money changes, verifies order went through
    # First things first. See what MtGox Orders think is there.
    OrderInfo = Trader._BTCInstance.GetInfo("Orders")

    # Next See What Database thinks is happening.
    db = Trader._BTCInstance.DBConnect()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM Trades  WHERE Status = 0;")
    ActiveOrders = cursor.fetchall()

    ## Use Cursor multiple times -- Could be dangerous! See how it plays

    ## Compare Orders -- Update Database Where Neccessary.

    ## Check 1 - Make Sure online orders ALL match ones in DB.
    ## If they don't. ERROR, Throw Exception!!!
    ## Check 2 - Set any orders to confirmed if they are no longer registered online and Cash or BTC have increased.
    ## If they are not online and cash or BTC have not increased Throw error. This could happen legitmately throuout multiple
    ## orders, but to be safe.... let it crash.
    ## Update 1 - Update Status's for records in our DB if orders have been completed.
    ## Check 3 - Check if an order has been waiting for longer than the allowed time. If so. Cancel it.

    for DBOrder in ActiveOrders:
        ## Check to see if it matches online. ## Allow a 5 second difference between online time and db time.
        Matched = False
        for OnlineOrder in OrderInfo:
            if (OnlineOrder['oid'] == DBOrder[9]):
                    ## Then we have a match. ## Double Check the types
                    Matched = True
                    ## Update Table with Effective Amount. # Don't want this anymore
                    #  cursor.execute("UPDATE Trades SET EffectiveAmount = " + str(int(OnlineOrder['effective_amount']['value_int'])/BTCFraction) + " WHERE ID = " + str(DBOrder[0]) +";" )
                    #db.commit()
                    ## Check for orders that have been taking along time.
                    if datetime.datetime.now() - datetime.datetime.fromtimestamp(OnlineOrder['date']) > timedelta(minutes=Trader._UnconfirmedOrderTime):
                        ## Cancel the order.
                        Trader._BTCInstance.CancelOrder(DBOrder[9])
                        ## Update the DB Record
                        cursor.execute("UPDATE Trades SET Status = -1, StatusString = \"CANCELED\" WHERE ID = " + str(DBOrder[0]) + ";")
                        db.commit()
                        ## If we just cancelled a sell order. Set the BUY status back to confirmed (1).
                        if DBOrder[2] == "SELL":
                            cursor.execute("UPDATE Trades SET Status = 1, StatusString = \"CONFIRMED\" WHERE ID = " + str(DBOrder[10]) + ";")
                            db.commit()
                    break
        ## Clear the cursor
        cursor.fetchall()
        ## If the Database Order is not online - Then has proabably been completed.
        if Matched is False:
            # Check before the trade and check now, and see if our account
            # balance has changed.
            ## Before Balance ##
            cursor.execute("SELECT BTCBefore, AUDBefore FROM Funds WHERE TradeID = " + str(DBOrder[0]) + ";")
            Data = cursor.fetchall()
            BTCBefore = Data[0][0]
            AUDBefore = Data[0][1]

            if DBOrder[2] == "BUY":
                if Trader.TotalBitCoins > float(BTCBefore): # Then our order went through as we have more BTC
                    ## Update our DB. This order is now confirmed
                    cursor.execute("UPDATE Trades SET Status = 1, StatusString = \"CONFIRMED\" WHERE ID = " + str(DBOrder[0]) + ";")
                    cursor.execute("UPDATE Funds SET BTCAfter = " + str(Trader.TotalBitCoins) + ", AUDAfter = " + str(Trader.TotalCash) + " WHERE TradeID = " + str(DBOrder[0]) + ";")
                    db.commit()
                else: ## This order hasn't changed Bitcoins... something is wrong. Throw exception
                    raise Exception("In CheckOrders() - Error - Cannot find BUY order online and BTC have not increased. Consult Log and Database")
                    return False
            if DBOrder[2] == "SELL": # We are selling an item. If this is sold we also have to update its partner.
                if Trader.TotalCash > float(AUDBefore):
                    ## UpdateDB - Set finished for the selling item and the buying item.
                    cursor.execute("UPDATE Trades SET Status = 3, StatusString = \"FINISHED\" WHERE ID IN (" + str(DBOrder[0]) + "," + str(DBOrder[10]) + ");")
                    ## Also we have just completed a BUY/SELL Trade. So add it to the Summary Table
                    cursor.execute("UPDATE Funds SET BTCAfter = " + str(Trader.TotalBitCoins) + ", AUDAfter = " + str(Trader.TotalCash) + " WHERE TradeID = " + str(DBOrder[0]) + ";")
                    ## Clear Cursor
                    cursor.fetchall()
                    ## Find Original Buy Price and Trade Fee
                    cursor.execute("SELECT Price, Amount, Total FROM Trades WHERE ID = " + str(DBOrder[10]) + ";")
                    OriginalData = cursor.fetchall()
                    BuyPrice        = OriginalData[0][0]
                    OriginalAmount  = OriginalData[0][1]
                    BuyTotal        = OriginalData[0][2]

                    Profit = (DBOrder[3]-BuyPrice)*OriginalAmount
                    ActualProfit = DBOrder[7] - BuyTotal
                    OverallFee = 1- ActualProfit/Profit
                    SummaryHeaders = "BuyTradeID, BuyPrice, SellPrice, Amount, OverallFee, RawProfit, ActualProfit"
                    SummaryValues = str(DBOrder[10]) + "," + str(BuyPrice) + "," + str(DBOrder[3]) + "," + str(OriginalAmount) + "," + str(OverallFee) + "," + str(Profit) + "," + str(ActualProfit)
                    cursor.execute("INSERT INTO TradeSummary ( " + SummaryHeaders + ") VALUES ( " + SummaryValues + ");")
                    db.commit()
                else:
                    raise Exception("In CheckOrders() - Error - Cannot find SELL order online and AUD has not incremented")
                    return False

    cursor.close()
    db.close()

    return True

def BuyCoins(Trader, CurrentOrders):
    ## We have spare orders, price should be increasing. Lets Buy some fucking BTC!!!
    ## Calculate how many BTC to buy.
    ## Make sure we have waited the appropriate time before placing an order.

    ## Connect to our DB ##
    db = Trader._BTCInstance.DBConnect()
    cursor = db.cursor()
    ## Find last buy time
    cursor.execute("SELECT max(Time) FROM Trades WHERE Status IN (0,1,2) and Type = \"BUY\";")
    LastTime = cursor.fetchall()[0][0]
    cursor.close()
    db.close()

    ## Check that we have waited long enough ##
    if LastTime is None or datetime.datetime.now() - LastTime > timedelta(minutes=Trader._OrderTime): # Then we have waited long enough.
        # Calculate the amount of BTC to order
        ## This is more complicated that you would expect. But due to only using a percentage of total amount.
        # have to use some maths - This makes all trades even
        Money2Spend = Trader.AllowedCash/(Trader._SimOrders-CurrentOrders*Trader._PercentageToTrade/100)
        BTC2Order = round(Money2Spend/Trader.CurrentPrice,8) ## Round to 8 Decimal Places (BTC Decimal places)

        # Order the BTC
        Result = Trader._BTCInstance.OrderBTC('BUY', BTC2Order, Trader.CurrentPrice)
        if Result == -1:
            return "Failure"
        ## Result returns Order ID - We add this in the DB next...

        ## Add Order details to Database ##
        db = Trader._BTCInstance.DBConnect()
        cursor = db.cursor()
        TradeHeaders = "Time, Type, Price, Amount, EffectiveAmount, Total, EffectiveTotal, TradeFee, OrderID,Status, StatusString"
        FundsHeaders = "TradeID, BTCBefore, AUDBefore"
        TradeValues = "NOW(),\"BUY\"," + str(Trader.CurrentPrice) + "," + str(BTC2Order) + "," + str(BTC2Order*(1-Trader.TradeFee/100)) + "," + str(Trader.CurrentPrice*BTC2Order) + "," + str(BTC2Order*(1-Trader.TradeFee/100)*Trader.CurrentPrice) + "," + str(Trader.TradeFee) +  ",\"" + Result + "\", 0, \"ORDERED\""
        FundsValues = "LAST_INSERT_ID()," + str(Trader.TotalBitCoins) + "," + str(Trader.TotalCash)
        try:
            cursor.execute("INSERT INTO Trades (" + TradeHeaders + ") VALUES ( " + TradeValues + ");")
            db.commit()
            cursor.execute("INSERT INTO Funds (" + FundsHeaders + ") VALUES ( " + FundsValues + ");")
        except:
            cursor.close()
            db.close()
            raise Exception("Couldn't add BUY order details to database")
        cursor.close()
        db.commit()
        db.close()

    else:
        return "Success - To soon to buy"

    return "Success"


def SellCoins(Trader):
    ## Search for Orders that need to be sold. Price is going down.
    ## For each order, we should have the order amount of BTC in our account.
    ## If not we need to account for the transaction fee HERE. Shit will break.

    ## Assuming we have BTC for each order.

    ## Find all buy orders awaiting a sell.
    db = Trader._BTCInstance.DBConnect()
    cursor = db.cursor()
    cursor.execute("SELECT ID, Price, EffectiveAmount FROM Trades WHERE Status = 1 and Type = \"BUY\";")
    Orders = cursor.fetchall()

    ## Going to Try keep this DB Connection Active throughout the looping. May Fuck out on me!! CHECK THIS!!!
    ## Set up Insert Vars
    TradeHeaders = "Time,Type, Price, Amount,EffectiveAmount,  Total, EffectiveTotal,TradeFee, OrderID,Partner, Status, StatusString "
    FundsHeaders = "TradeID, BTCBefore, AUDBefore"
    FundsValues = "LAST_INSERT_ID()," + str(Trader.TotalBitCoins) + "," + str(Trader.TotalCash)

    ## Have we sold anything?
    Sold = False
    ## Loop Through Orders, check which have exceeded our MinPercentage
    for Order in Orders:
        if (float(Order[1])*(1 + Trader._MinPercent/100) <= Trader.CurrentPrice): ## Then we want to sell
            ## Place a sell order
            Result = Trader._BTCInstance.OrderBTC("SELL", float(Order[2]), Trader.CurrentPrice)
            if Result == -1:
                return "Failure"
            Sold = True
            ## Insert Order Details into DB
            try:
                cursor.execute("INSERT INTO Trades ( " + TradeHeaders + ") VALUES (NOW() ,\"SELL\"," + str(Trader.CurrentPrice) + "," + str(Order[2]) + "," + str(Order[2]) + "," + str(float(Order[2])*Trader.CurrentPrice) + "," + str(float(Order[2])*Trader.CurrentPrice*(1 - Trader.TradeFee/100)) + "," + str(Trader.TradeFee) + ",\"" + Result + "\","  + str(Order[0]) + "," + "0, \"ORDERED\" );")
                db.commit()
                cursor.execute("INSERT INTO Funds (" + FundsHeaders + ") VALUES ( " + FundsValues + ");")
                ## Update the BUY Trade to set to "SELLING" status
                cursor.execute("UPDATE Trades SET Status = 2, StatusString = \"SELLING\" WHERE ID = " + str(Order[0]) + ";")
            except:
                cursor.close()
                db.close()
                raise Exception("Couldn't add SELL Order details to database")

    cursor.close()
    db.commit()
    db.close()

    if Sold is False:
        return "Success - Price not high enough yet"

    return "Success"


def GetUseableCurrencyAndFee(Trader):

    (AvailableBTC, AvailableFunds, TradeFee) = Trader._BTCInstance.GetUseableCurrencyAndFee()

    return (AvailableBTC, AvailableFunds, TradeFee)


def CurrentOrders(Trader):
    db = Trader._BTCInstance.DBConnect()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM Trades WHERE Status = 1 and Type = \"BUY\";")
    SellOrderCount = cursor.fetchall()[0][0]
    cursor.execute("SELECT COUNT(*) FROM Trades WHERE Status IN (0,1,2) and Type=\"BUY\";")
    BuyOrderCount = cursor.fetchall()[0][0]
    cursor.close()
    db.close()

    return (BuyOrderCount, SellOrderCount)


