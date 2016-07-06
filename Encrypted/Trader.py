#!/usr/bin/python
#Modules
from time import sleep
import os
import sys
## Get Custom Libraries from Libraries Folder
sys.path.append(os.getcwd() + '/Libraries')
## Get Hash from File
Hashin= open("Temp.dat", "rb")

## Custom - Reference from Libraries Folder
os.chdir("./Libraries")

## Import Libraries ##
import DM
Hash = Hashin.read()
Hashin.close()
DM.DecryptModules(Hash, ["EBitCoinInterface","ETraderMain"])
from BitCoinInterface import BitCoinInterface
from TraderMain import Trader

## Global Variables ##
####################################
## Decide logic if market crashes
## Trader Symantics ##
TraderFlag                  = False              # Run with AI and Trading Algorithms
DataCollect                 = True              # Run this to collect data. Can therefore run a datacollector. And a trader.
RunPeriod                   = 30                # In Seconds - How often to update data
LogTrader                   = True              # Write a log
HomeCurrency                = 'AUD'             # Currency to read/write view and store in DB
TradeCurrency               = 'USD'             # Currency to trade with. Accounts will use USD.
MultiMarketPrediction       = False             # Using other markets creates ghost fluctuations. As MtGox wont buy/sell from other markets unless there is a 2.5% premium difference.
## AI Specific ##
RetrainAIInterval           = 15                 # In Mins - How long before retraining
AILearningLifetime          = 48                # In Hours
PercentageChangeToPredict   = 2                 # This is the percentage the AI is predicting. Can define a list.
PeriodsToPredict            = [10,20,30,45,60,90,120,150,180]          # Average Over Predictive successes
AcceptanceThreshold         = 0.4               # Threshold before we classify a positive or negative. Higher value = safer betting.
AIType                      = "RandomForest"    # Choice of "SVM", "RandomForest"
## BUY/SELL Trade Specific ##
PercentageOfTotalMoney      = 95                # Percentage of Money in the account to trade with.
RequiredPredictionsToBuy    = 3
RequiredPredictionsToSell   = 2                 # Can specify how 'scared' we are. If this is smaller it is safer, but we may not reach high peaks. More suceptible to fluctuations.
SimultaneousOrders          = 4                 # How many orders can the trader have at once.
TimeBetweenOrders           = 10                # In Mins
TimeToHoldUnconfirmedOrders = 5                 # In Mins
MinPercentageToGain         = 2                 # No orders will be sold less than this percentage
####################################



## Trader Main Procedure ##
def main(BTCInstance):
    ## BTCInstance - Is the instance of the BitCoinModules Class which specifies currencies, codes and acouunts.
    ## Parameter Logic ##
        if TimeBetweenOrders <=  RunPeriod/60:
            print("Cannot have OrderTime less than RunTime. Will cause orders to get mixed up")
            return -1

        if TraderFlag:
            ## Set up Trading Parameters ##
            ParameterData = []
            ParameterData.append(AILearningLifetime)
            ParameterData.append(PercentageChangeToPredict)
            ParameterData.append(PeriodsToPredict)
            ParameterData.append(AcceptanceThreshold)
            ParameterData.append(AIType)
            ParameterData.append(RequiredPredictionsToBuy)
            ParameterData.append(RequiredPredictionsToSell)
            ParameterData.append(SimultaneousOrders)
            ParameterData.append(TimeBetweenOrders)
            ParameterData.append(TimeToHoldUnconfirmedOrders)
            ParameterData.append(MinPercentageToGain)
            ParameterData.append(AIType)
            ParameterData.append(PercentageOfTotalMoney)
            ParameterData.append(LogTrader)
            ParameterData.append(True) ## Running in Real-time
            ParameterData.append(BTCInstance)

            ## Initialize Trader Class
            TraderClass = Trader(ParameterData)
        ## Initialize Common Variables
        LastAverage = 0
        InitialTrain = False        # Flag to start an intial training. Has to happen once data is read
        Iteration = 0               # Used to count for when to retrain AI
        Saved = True
        while(1):
                os.system('clear')

                ## Get Data from Server - Convert Currency to Home Currency
                if DataCollect:
                    RawData = BTCInstance.GetRawData()
                    if RawData is False:
                        continue

                    ## Get Last Datapoint to find Missing Trades ##
                    LastEntryTimeStamp = BTCInstance.GetLastTimeAndPrice()[0]

                    ## Get all Trades up to now and average them ##
                    Trades      = BTCInstance.GetRecentTrades(LastEntryTimeStamp)
                    LastAverage = BTCInstance.CalculateTradeAverages(Trades, RawData, LastAverage)

                    ## I want the Avg of all Countries Printed Also
                    print("\nAvgPrice: {:.2f}    AvgVol: {:.4f}\n".format(RawData['AvgPrice'], RawData['AvgVol']))

                    ## Store Data ##
                    Saved = BTCInstance.SaveRawData(RawData)

                if TraderFlag and Saved:
                    ## Give the current time stamp and price to our trader.
                    (TraderClass.CurrentTimeStamp, TraderClass.CurrentPrice) = BTCInstance.GetLastTimeAndPrice()
                    ## Re-Train our AI If necessary. # Also update our Exchange Rates
                    if InitialTrain is False or (Iteration*RunPeriod/60 > RetrainAIInterval):

                        TraderClass.TrainAI()
                        Iteration = 0
                        ## Update Exchange Rates, if its not the first time.
                        if InitialTrain:
                            BTCInstance.UpdateExchangeDict()

                        InitialTrain = True


                    ## If We obtained new data, Run our Trading Alogrithms.
                    TraderClass.TradeBitCoins()


                Iteration += 1
                print("Sleeping...")
                sleep(RunPeriod)


if __name__ == "__main__":
    try:
        ## Remove Files ##
        os.remove("BitCoinInterface.py")
        os.remove("TraderMain.py")
        #Generate Hash for API keys
        ## Initialize an instance of our BitCoinModules interface
        os.chdir("../")
        BTCInstance = BitCoinInterface([HomeCurrency, TradeCurrency, MultiMarketPrediction, Hash])

        # Save PID of File
        PIDFile = open("TraderPID.pid", "w")
        PIDFile.write(str(os.getpid()))
        PIDFile.close()

        # Run Main
        main(BTCInstance)

    ## Error Catching. Log Errors
    except KeyboardInterrupt:
        ## Remove PID File
        os.remove("TraderPID.pid")
        exit(5)
    except Exception:
        ## Log the Exception
        import traceback
        import datetime
        ErrorDump = open("TraderErrors.log", "a")
        ErrorDump.write(str(datetime.datetime.now()) + ":"+ "\n")
        for Error in traceback.format_exception(*sys.exc_info()):
            ErrorDump.write(Error + "\n")
        ErrorDump.close()
        raise
