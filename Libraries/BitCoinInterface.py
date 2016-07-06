## This class Does the inferfacing with MtGox Exchange.
## It takes HomeCurrency and TradingCurrency Parameters. So that it can trade in any market, but we visually see
## Home currency here.

## Import Required Modules ##

## Authentication Modules
import hmac, base64, hashlib
##HTTP Modules
from urllib.request import urlopen, Request
import urllib.error
import urllib.parse
import socket
##Generic Modules
import sys, time
import json #Decoding Javascript Object
from datetime import datetime
## Encryption Modules ##
from Crypto.Cipher import AES
##DB Modules
import pymysql


## Database Variables to be global - So AI can use it without Initializing a class.

def LoadConfig(Hash, ConfigFile):
    File = open(ConfigFile, "rb")
    Data = File.read()
    File.close()
    iv = Data[:AES.block_size]
    cipher = AES.new(Hash, AES.MODE_CFB, iv)
    try:
        Contents = cipher.decrypt(Data[AES.block_size:]).decode()
    except UnicodeDecodeError:
        print("Incorrect Security Key. Cannot load data")
        raise Exception("Incorrect Security Key")

    Contents = Contents.rstrip()

    return Contents.split(',')


class BitCoinInterface:

    def __init__(self,Data):
        ## Data can be any of
        # (HomeCurrency, TradeCurrency, MultiMarketPrediction,APIDBHash)
        # (HomeCurrency, TradeCurrency, MultiMarketPrediction,APIDBHash, ExchangeDict)

        ## Trade Paths ###
        self._AUDTradePath = 'BTCAUD/money/trades/fetch'
        self._USDTradePath = 'BTCUSD/money/trades/fetch'
        self._EURTradePath = 'BTCEUR/money/trades/fetch'
        self._ExchangePath = "http://rate-exchange.appspot.com/currency" # I previously used this real-time. Put me out from MtGox
        self._MtGoxExchangePath = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml" # MtGox uses these exchanges

        ## Database Calculations ##
        self._MovingAverages =  [5, 10, 15, 30, 60, 90]
        self._GradientPeriods = [5, 10, 15, 30, 60, 90]

        ## MtGox Currency Fraction Conversions ##
        self._CurFraction = {"BTC":1e8, "AUD":1e5, "USD":1e5, "EUR":1e5, "GBP":1e5, "JPY":1e3}
        ## Instead of building a rounding dictionary. Will round all currencies to 5dp.

        ###### Handle Parameter Input - After we have loaded variables ##########
        if len(Data) == 4:
            self._HomeCurrency    = Data[0]
            self._TradeCurrency   = Data[1]
            self._MultiMarketPrediction = Data[2]
            self._Hash           = Data[3]
            self.UpdateExchangeDict()

        if len(Data) == 5:
            self._HomeCurrency    = Data[0]
            self._TradeCurrency   = Data[1]
            self._MultiMarketPrediction = Data[2]
            self._Hash            = Data[3]
            self._ExchangeDict    = Data[4]

        if self._HomeCurrency not in self._ExchangeDict.keys() or self._TradeCurrency not in self._ExchangeDict.keys():
            raise Exception("Home or Trade Currencies have no known conversion. Cannot run!!!")

        ## Security Keys ##
        (self._APIKey, self._SecretKey) = LoadConfig(self._Hash, "APIKeys.cfg")

        ## Intialise DB Variables from External Config. Can then be accesssed through the class
        (self._User,self._Pwd, self._DB, self._Host, self._Socket)  = LoadConfig(self._Hash, "DBConfig.cfg")

        ## Paths
        self._Base = 'https://data.mtgox.com/api/2/'
        self._RatePath = 'BTC' + self._TradeCurrency + '/money/ticker_fast'
        self._AccountInfoPath = 'BTC' + self._TradeCurrency + '/money/info'
        self._OrdersPath = 'BTC' + self._TradeCurrency + '/money/orders'
        self._OrderAddPath = 'BTC' + self._TradeCurrency + '/money/order/add'
        self._CancelOrderPath = 'BTC' + self._TradeCurrency + '/money/order/cancel'

        ## For Convenience - and code simplification
        self._Trade2HomeRate = self._ExchangeDict[self._HomeCurrency]/self._ExchangeDict[self._TradeCurrency]
        self._Home2TradeRate = 1/self._Trade2HomeRate

    def DBConnect(self):
        connection = pymysql.connect(host=self._Host, unix_socket=self._Socket, user=self._User, passwd=self._Pwd, db=self._DB)
        return connection


    ## Set up Request Function ##

    def makereq(self,key, secret, path, data):

        if data is not None:
            data = "nonce=" + str(int(time.time()*1000)) + "&" + data
        else:
            data = "nonce=" + str(int(time.time()*1000))

        postdata = path + chr(0) + data

        secret = base64.b64decode((secret.encode()))
        sha512 = hashlib.sha512

        H = hmac.new(secret, postdata.encode(), sha512).digest()
        sign = base64.b64encode(H)
        header = {
            'User-Agent': 'Age-Account',
            'Rest-Key': key,
            'Rest-Sign': sign,
        }
        #Error Catching outside this function.
        #try:
        result = urlopen(Request(self._Base + path, data.encode() , header), data.encode(), 10)
        #except Exception as error:
        #    print ("Could not connect")
        #    print ("Code:" + str(error.code))

        return result


    ## Find Account Info and Order Details ##

    def GetInfo(self,Type):
        if Type not in ['Account', 'Orders']:
            print("Wrong Type when getting info")
            return None

        if Type == "Account":
            Path = self._AccountInfoPath
        elif Type == "Orders":
            Path = self._OrdersPath

        Connected = False
        Tries = 0
        while(Connected is False):
            try:
                Response = self.makereq(self._APIKey, self._SecretKey, Path, None)
                if Response.getcode() == 200:
                    ResponseText = Response.readall().decode()
                    Info = json.loads(ResponseText)
                    if Info['result'] == 'success':
                        Connected = True
            except:
                print("Could not retrieve Account Info. Re-trying")
                Tries += 1
                if Tries > 5:
                    raise Exception("Cannot Get Account Info")

        ## Currency Conversion ##
        if Type == "Orders": # We have to loop through the orders
            for Order in Info['data']:
                Order['price']['value_int'] = self._ExchangeDict[self._HomeCurrency]/self._ExchangeDict[Order['currency']]*int(Order['price']['value_int'])

        if Type == "Account": ## Assume we only have 1 wallet in currency: TradeCurrency
            Info['data']['Wallets'][self._TradeCurrency]['Balance']['value_int'] = self._Trade2HomeRate*int(Info['data']['Wallets'][self._TradeCurrency]['Balance']['value_int'])

        return Info['data']

    def GetUseableCurrencyAndFee(self):

        AccountInfo = self.GetInfo("Account")
        ## Already converted Value_Int to Float through the exchange
        AvailableBTC = int(AccountInfo['Wallets']['BTC']['Balance']['value_int'])/self._CurFraction['BTC']
        AvailableFunds = AccountInfo['Wallets'][self._TradeCurrency]['Balance']['value_int']/self._CurFraction[self._HomeCurrency]

        ## Converted Precision to MtGox precision
        return (round(AvailableBTC,8), round(AvailableFunds,5), AccountInfo['Trade_Fee'])


    ## Cancel and Order ##
    def CancelOrder(self,OrderId):
        Canceled = False
        Attempts = 0
        Data = "oid=" + str(OrderId)
        while(Canceled is False):
            try:
                Response = self.makereq(self._APIKey, self._SecretKey, self._CancelOrderPath, Data)
                if Response.getcode() == 200:
                    ResponseText = Response.readall().decode()
                    Info = json.loads(ResponseText)
                    if Info['result'] == 'success':
                        Canceled = True
            except:
                print("Could not cancel order")
                Attempts += 1
                if Attempts > 5:
                    raise Exception("Cannot cancel the order: " + str(OrderId))
                    return 0
                time.sleep(1)
        return 1

    ## Gets normal data from server. Requires to API Keys - Simple Data Collection
    def GetRawData(self):

            try:
                MtGox = Request(self._Base + self._RatePath) ## Got rid of Fat data. Can now use ticker_fast
                Response = urlopen(MtGox, None, 10)
            except (urllib.error.HTTPError, urllib.error.URLError):
                print("HTTP Failure. Retrying")
                return False

            if Response.getcode() != 200:
                return False

            ResponseText = Response.readall().decode()
            ExchangeObject = json.loads(ResponseText)

            LastPriceOriginal = int(ExchangeObject["data"]["last"]["value_int"])/self._CurFraction[self._TradeCurrency]
            LastPrice = int(ExchangeObject["data"]["last"]["value_int"])*self._Trade2HomeRate/self._CurFraction[self._TradeCurrency]
            Now = int(ExchangeObject["data"]["now"])
            Buy = int(ExchangeObject["data"]["buy"]["value_int"])*self._Trade2HomeRate/self._CurFraction[self._TradeCurrency]
            Sell = int(ExchangeObject["data"]["sell"]["value_int"])*self._Trade2HomeRate/self._CurFraction[self._TradeCurrency]

            print("################################")
            print("Current Price: ${:.4f} {}     CurrentPrice ${:.4f} {}\n".format(LastPrice, self._HomeCurrency, LastPriceOriginal, self._TradeCurrency))
            print("Buy: {:.4f}      Sell: {:.4f}".format(Buy, Sell))
            print("Time: " + str(datetime.fromtimestamp(Now/1e6)))

            ReturnValue = dict()
            ReturnValue["LastPrice"] = LastPrice
            ReturnValue["UnixTimeStamp"] = Now
            ReturnValue["Buy"] = Buy
            ReturnValue["Sell"] = Sell

            return ReturnValue


    def OrderBTC(self,TypeString,BTC2Order, PricePerCoin):
        #TypeString: BUY or SELL
        #BTC2Order: Number of BTC to order
        #Price: Price/BTC To buy or sell
            if TypeString not in ['BUY','SELL']:
                return -1

            if TypeString == 'BUY':
                Type='bid'
            if TypeString == 'SELL':
                Type='ask'

            BTCInt = int(BTC2Order*self._CurFraction['BTC'])
            ## Convert Currency for Ordering
            PriceInt = int(PricePerCoin*self._Home2TradeRate*self._CurFraction[self._TradeCurrency])
            datastring = "type=" + Type + "&amount_int=" + str(BTCInt) + "&price_int=" + str(PriceInt)

            try:
                response = self.makereq(self._APIKey, self._SecretKey, self._OrderAddPath, datastring)
            except Exception as Error:
                print ("Order of type:", TypeString, " could not be established")
                print ("Details:")
                print ("BitCoins: ", BTC2Order)
                print("Price: ", PricePerCoin)
                print("Error:", Error.read())
                return -1

            ResponseText = response.readall().decode()
            ExchangeObject = json.loads(ResponseText)

            if ExchangeObject["result"] == "success":
                return ExchangeObject["data"] ## Return the Order ID
            else:
                return -1

    ## Saves Basic Data to the Database
    def SaveRawData(self, RawData):
        #DailyAverage, DailyWeightedVolumeAverage

        ## Connect to Database
        db = self.DBConnect()
        cursor = db.cursor()
        headers = "UnixTimeStamp, Price, AveragePrice, AverageVol, Buy, Sell"

        query = "INSERT INTO RawData(" + headers + ") VALUES (" + str(RawData["UnixTimeStamp"]) + "," +  str(RawData["LastPrice"]) + "," + str(RawData["AvgPrice"]) + "," + str(RawData["AvgVol"]) + ","  + str(RawData["Buy"]) + "," + str(RawData["Sell"]) + ");"
        try:
            cursor.execute(query)
            db.commit()
        except pymysql.err.IntegrityError as e:
            print("Caution. DB Error")
            print(e)
            return False

        ## Run Cleaning Procedures and Mathematical Functions ##

        ## Clean Data ##
        cursor.execute("CALL CleanAverages("+ str(RawData["UnixTimeStamp"])+ ");")
        ## Calculate Moving Averages ##
        for Period in self._MovingAverages:
            cursor.execute("CALL MovingAverages(" + str(RawData["UnixTimeStamp"]) + "," + str(Period)+ ");")

        ## Calculate the Gradients
        for Period in self._GradientPeriods:
                cursor.execute("CALL Gradients(" + str(RawData["UnixTimeStamp"]) + "," + str(Period)+ ");")

        db.commit()

        ## All went well. Return Success

        return True

    ## Gets the Last Time stamp that was recorded
    def GetLastTimeAndPrice(self):
        db = self.DBConnect()
        cursor = db.cursor()
        query = "SELECT UnixTimeStamp, AveragePrice FROM RawData WHERE UnixTimeStamp = (SELECT MAX(UnixTimeStamp) FROM RawData);"
        cursor.execute(query)
        Data = cursor.fetchone()
        LastTimeStamp = Data[0]
        AveragePrice = float(Data[1])
        cursor.close()
        db.close()

        return (LastTimeStamp, AveragePrice)



    ### Find Exchange Rates ##### - This only gets updates daily, but we'll check every 5 minutes
    def UpdateExchangeDict(self):
        ## Error Checking done inside this function
        Attempts = 0
        Connected = False
        while(Connected is False):
            try:
                Response = urlopen(self._MtGoxExchangePath)
                if Response.getcode() == 200:
                    Connected = True
            except (urllib.error.HTTPError, urllib.error.URLError) as Error:
                print("Could not load Currency Rates")
                import traceback
                import datetime
                ErrorDump = open("URLErrors.log", "a")
                ErrorDump.write(str(datetime.datetime.now()) + ":" + "\n")
                for Error in traceback.format_exception(*sys.exc_info()):
                    ErrorDump.write(Error + "\n")
                ErrorDump.write("Continuing... \n")
                ErrorDump.close()
                Attempts += 1
                if Attempts >= 5:
                    return -1
        import xml.etree.ElementTree as ET
        root = ET.fromstring(Response.readall())
        ExchangeDict = dict()
        for Rates in root[2][0]:
            ExchangeDict[Rates.attrib['currency']] = float(Rates.attrib['rate'])
        ExchangeDict['EUR'] = 1

        self._ExchangeDict = ExchangeDict


    ## Depreciated - Not used by MtGox
    def GetExchangeRateCurrent(self,CurrencyFrom, CurrencyTo):
        ## Error Checking done inside this function
        Attempts = 0
        Connected = False
        while(Connected is False):
            try:
                Response = urlopen(self._ExchangePath + "?from=" + CurrencyFrom + "&to=" + CurrencyTo)
                if Response.getcode() == 200:
                    Connected = True
            except (urllib.error.HTTPError, urllib.error.URLError) as Error:
                print("Could not load Currency Rates")
                import traceback
                import datetime
                ErrorDump = open("URLErrors", "a")
                ErrorDump.write(str(datetime.datetime.now()) + ":" + "\n")
                for Error in traceback.format_exception(*sys.exc_info()):
                    ErrorDump.write(Error + "\n")
                ErrorDump.write("Continuing... \n")
                ErrorDump.close()
                Attempts += 1
                if Attempts >= 5:
                    return -1
        Object = json.loads(Response.readall().decode())

        return Object["rate"]

    def GetRecentTrades(self,TradeStamp):
        #This is done not using the makereq function as no user data is required.
        # Finds US, EUR and AUD trades since the timestamp given.

        if TradeStamp is None:
            return dict()

        if self._MultiMarketPrediction:
        #Define Local Vars
            AUDDict = dict() #Stores AUD trades
            USDDict = dict() #Stores USD trades
            EURDict = dict() #Stores EUR trades
            AUDToHomeRate = self._ExchangeDict[self._HomeCurrency]/self._ExchangeDict['AUD']
            USDToHomeRate = self._ExchangeDict[self._HomeCurrency]/self._ExchangeDict['USD']
            EURToHomeRate = self._ExchangeDict[self._HomeCurrency]/self._ExchangeDict['EUR']

            try:
                AUDResponse = urlopen(self._Base + self._AUDTradePath + "?since=" + str(TradeStamp), None, 3)
                USDResponse = urlopen(self._Base + self._USDTradePath + "?since=" + str(TradeStamp), None, 3)
                EURResponse = urlopen(self._Base + self._EURTradePath + "?since=" + str(TradeStamp), None, 3)
            except (urllib.error.HTTPError, socket.error, socket.timeout, urllib.error.URLError): #as Error:
                print("Could not retrieve trades")
                #print("Error: ", str(Error.read()))
                return dict()

            ResponseTextAUD = AUDResponse.readall().decode()
            ResponseTextUSD = USDResponse.readall().decode()
            ResponseTextEUR = EURResponse.readall().decode()

            ExchangeObjectAUD = json.loads(ResponseTextAUD)
            ExchangeObjectUSD = json.loads(ResponseTextUSD)
            ExchangeObjectEUR = json.loads(ResponseTextEUR)


            for Trades in ExchangeObjectAUD["data"]:
                if Trades["primary"] == "Y":
                    AUDDict[Trades["date"]] = {"price": int(Trades["price_int"])*AUDToHomeRate/self._CurFraction['AUD'], "amount": int(Trades["amount_int"])/self._CurFraction['BTC'], "id": int(Trades["tid"])}

            for Trades in ExchangeObjectUSD["data"]:
                if Trades["primary"] == "Y":
                    USDDict[Trades["date"]] = {"price": int(Trades["price_int"])*USDToHomeRate/self._CurFraction['USD'], "amount": int(Trades["amount_int"])/self._CurFraction['BTC'], "id": int(Trades["tid"])}

            for Trades in ExchangeObjectEUR["data"]:
                if Trades["primary"] == "Y":
                    EURDict[Trades["date"]] = {"price": int(Trades["price_int"])*EURToHomeRate/self._CurFraction['EUR'], "amount": float(Trades["amount_int"])/self._CurFraction['BTC'], "id": int(Trades["tid"])}

            return dict(list(EURDict.items()) + list(USDDict.items()) + list(AUDDict.items()))


        else: ## Just use the highest vol market, USD
            USDDict = dict() #Stores USD trades
            USDToHomeRate = self._ExchangeDict[self._HomeCurrency]/self._ExchangeDict['USD']

            try:
                USDResponse = urlopen(self._Base + self._USDTradePath + "?since=" + str(TradeStamp), None, 3)
            except (urllib.error.HTTPError, socket.error, socket.timeout, urllib.error.URLError): #as Error:
                print("Could not retrieve trades")
                #print("Error: ", str(Error.read()))
                return dict()

            ResponseTextUSD = USDResponse.readall().decode()
            ExchangeObjectUSD = json.loads(ResponseTextUSD)

            for Trades in ExchangeObjectUSD["data"]:
                if Trades["primary"] == "Y":
                    USDDict[Trades["date"]] = {"price": int(Trades["price_int"])*USDToHomeRate/self._CurFraction['USD'], "amount": int(Trades["amount_int"])/self._CurFraction['BTC'], "id": int(Trades["tid"])}

            return USDDict




    ## Calculate the average price given a set of trades. If there are no trades, use the last value
    def CalculateTradeAverages(self,Trades,RawData, LastAverage):

        SumPrice = 0
        TradeNo = 0
        SumVol = 0
        if Trades != {}:
            for Trade in Trades.keys():
                TradeNo += 1
                ## Weighted Average for the fetched trades
                SumPrice += Trades[Trade]["price"]*Trades[Trade]["amount"]
                SumVol += Trades[Trade]["amount"]

            RawData["AvgVol"] = SumVol/TradeNo
            RawData["AvgPrice"] = round(SumPrice/SumVol, 5)

        else:
            RawData["AvgVol"] = 0
            RawData["AvgPrice"] = LastAverage

        return RawData["AvgPrice"]
