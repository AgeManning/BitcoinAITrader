## Import Necessary Modules
from datetime import datetime ## For Logging

class Trader:

    # Logging Function

    def Log(self,Message):
        if self._Log:
            self.LogFile = open("BTCLogFile.log", "a")
            self.LogFile.write(Message)
            self.LogFile.close()

    def __init__(self, Data):
        # RealTime - Boolean - Whether to train the AI in real-time (Ie - No
        # future data is known)

        # Initialize Variables
        self._AITrainingHours           = Data[0]
        self._PercentageChangeToPredict = Data[1]
        self._PeriodsToPredict          = Data[2]
        self._AcceptanceThreshold       = Data[3]
        self._AIKey                     = Data[4]
        self._ReqPredictionsBuy         = Data[5]
        self._ReqPredictionsSell        = Data[6]
        self._SimOrders                 = Data[7]
        self._OrderTime                 = Data[8]
        self._UnconfirmedOrderTime      = Data[9]
        self._MinPercent                = Data[10]
        self._AIType                    = Data[11]
        self._PercentageToTrade         = Data[12]
        self._Log                       = Data[13]
        self._RealTime                  = Data[14]
        self._BTCInstance               = Data[15]

        # Intialization Thingys
        self.PredictionList = [0]*max(self._ReqPredictionsBuy, self._ReqPredictionsSell)
        self.AveragePredList = [0]*max(self._ReqPredictionsBuy, self._ReqPredictionsSell)
        #(self.TotalBitCoins, self.TotalCash)  = self.self._TraderDacInst.GetUseableCurrency()

        #Import Encrypted Modules
        import os
        os.chdir("./Libraries")
        import DM
        DM.DecryptModules(self._BTCInstance._Hash, ["EAI","ETraderDac"])
        import AI
        import TraderDac
        self._AIClass = AI
        self._TraderDac = TraderDac
        #Remove Unencrypted Files
        os.remove("AI.py")
        os.remove("TraderDac.py")
        os.chdir("../")

    def __del__(self):
        del self.AI


    def TrainAI(self):
        # Ensure Garbage Collection Works.
        # Delete and re-initialize manually if need to.
        ## Build Parameter List for AI
        ParameterData= []
        ParameterData.append(self.CurrentTimeStamp)
        ParameterData.append(self._PeriodsToPredict)
        ParameterData.append(self._AITrainingHours)
        ParameterData.append(self._PercentageChangeToPredict)
        ParameterData.append(self._AcceptanceThreshold)
        ParameterData.append([self._AIType]) ## AI Can train multiple AI Alogrithms. Parameter is a list of AI
        ParameterData.append(self._BTCInstance.DBConnect) ## Give it a function to connect to the DB
        self.AI = self._AIClass.AI(ParameterData)
       ## Train the AI
        self.AI.TrainAI(self._RealTime)


    def TradeBitCoins(self):
        # AI is the AI Class

        ## Check Current Monies ##
        (self.TotalBitCoins, self.TotalCash, self.TradeFee)  = self._TraderDac.GetUseableCurrencyAndFee(self)
        self.TotalCash = self.TotalCash
        self.AllowedCash = self.TotalCash*(self._PercentageToTrade/100)
        ## Check Status's of Current Orders ##
        if self._TraderDac.CheckOrders(self) is False:
            return -1
        (BuyOrderCount, SellOrderCount) = self._TraderDac.CurrentOrders(self)

        ## Obtain Predictions - Changed to allow multiple AI ##
        (Refined, AvgPrediction) = self.AI.Predict(self.CurrentTimeStamp, self._AIKey)
        self.PredictionList.pop(0)
        self.PredictionList.append(Refined)
        self.AveragePredList.pop(0)
        self.AveragePredList.append(AvgPrediction)

        print("TotalBTC: {}   TotalCash: {}".format(self.TotalBitCoins, self.TotalCash))
        print("Predictions:")
        print("Actual: {}      Average: {} ".format(self.PredictionList,['%.2f' % el for el in self.AveragePredList]))

        ## Buy/Sell Logic ##
        # Implemented as Follows:
        # Buy if we predict a positive price increase.
        # Maintain a list of bought orders..
        # If we predict a negative... Sell any of the orders provided we have
        # made a profit

        # If we are predicting Positive Rise #
        if min(self.PredictionList[-self._ReqPredictionsBuy:]) == 1 and max(self.PredictionList[-self._ReqPredictionsBuy:]) == 1 and BuyOrderCount < self._SimOrders:
            ## Order BitCoins ##
            self.Log(str(datetime.now()) + ":\n")
            self.Log("BTC: {}     AUD: {} \n".format(self.TotalBitCoins,self.TotalCash))
            self.Log("AUD allowed to spend: {}".format(self.AllowedCash))
            self.Log("RefinedPred: {}      AveragePred: {} \n".format(self.PredictionList,['%.2f' % el for el in self.AveragePredList]))
            self.Log("CurrentOrders: Sell: {}      Buy: {}  \n".format(SellOrderCount,BuyOrderCount))
            self.Log("CurrentPrice: {:.2f}\n".format(self.CurrentPrice))
            self.Log("Buying BTC:")
            Result = self._TraderDac.BuyCoins(self, BuyOrderCount)
            self.Log(Result + "\n")


        if min(self.PredictionList[-self._ReqPredictionsSell:]) == -1 and max(self.PredictionList[-self._ReqPredictionsSell:]) == -1 and SellOrderCount > 0:
            ## Sell BTC
            self.Log(str(datetime.now()) + ":\n")
            self.Log("BTC: {}     AUD: {} \n".format(self.TotalBitCoins,self.TotalCash))
            self.Log("RefinedPred: {}      AveragePred: {} \n".format(self.PredictionList,['%.2f' % el for el in self.AveragePredList]))
            self.Log("CurrentOrders: Sell: {}      Buy: {}  \n".format(SellOrderCount,BuyOrderCount))
            self.Log("CurrentPrice: {:.2f}\n".format(self.CurrentPrice))
            self.Log("Selling BTC:")
            Result = self._TraderDac.SellCoins(self)

            self.Log(Result + "\n\n")

