#!/usr/bin/python
from sklearn import svm
from sklearn.ensemble import RandomForestClassifier
import numpy  # Store Set Data as N Dimensional Array

class AI:
    ## Main Variables Defined in constructor ##
    # _CurrentTimeStamp
    # _SuccessPerMinsList
    # _TrainingHours
    # _PercentageChange
    # _TestMinStamp
    # _TestMaxStamp
    # _AITypeArray
    # _TrainedAI

    def BuildAI(self,AIType):
        #This builds the default AIArray container. Which is required to hold a number of AI
        #Algorithms as many need to be calculated with different SuccessPeriods.

        ## AI Algorithms ##
        ## SVM - Using a polynomial Kernel
        if AIType == "SVM":
            SVMDegree = 10
            AISVMPoly = svm.SVC(kernel="poly", degree=SVMDegree)
            #Can add max_features = Number of features. Will leave it for now.
            return AISVMPoly

        if AIType == "RandomForest":
            ForestEst = 40 #Number of trees in forest.
            AIRandomForest = RandomForestClassifier(n_estimators=ForestEst,max_depth=None, min_samples_split=1, random_state=0)
            return AIRandomForest


    def __init__(self,Data):
        ## Data is either Default, for default constructor or list:
        ## Data[0] = CurrentTimeStamp
        ## Data[1] = SuccessPeriodMinsList
        ## Data[2] = TrainingHours
        ## Data[3] = PercentageChange

        if len(Data) == 0: ## Need to Initialize a DBConnect() somewhere
            self._DBConnect = None ## If testing - Create a connection to the Database
            self._CurrentTimeStamp = 1367470819102592
            self._SuccessPeriodMinsList = range(5,95,10)
            self._TrainingHours = 10
            self._PercentageChange = 2
            self._AcceptanceThreshold = 0.4
            ## Testing Parameters
            self._TestMinStamp = 1367470819102592
            self._TestMaxStamp = 1367495166360072
            self._TestPercentageChange = 2
            self._AcceptanceThreshold = 0.4
            self._AITypeArray = ["SVM","RandomForest"]
        elif len(Data) == 7:                            # No Training Parameters
            self._CurrentTimeStamp = Data[0]
            self._SuccessPeriodMinsList = Data[1]
            self._TrainingHours = Data[2]
            self._PercentageChange = Data[3]
            self._AcceptanceThreshold = Data[4]
            self._AITypeArray = Data[5]
            self._DBConnect = Data[6] ## This is the reference to the DBConnect function.
        elif len(Data) == 9:
            self._CurrentTimeStamp = Data[0]
            self._SuccessPeriodMinsList = Data[1]
            self._TrainingHours = Data[2]
            self._PercentageChange = Data[3]
            self._TestMinStamp = Data[4]
            self._TestMaxStamp = Data[5]
            self._TestPercentageChange = Data[6]
            self._AcceptanceThreshold = Data[7]
            self._AITypeArray = Data[8]
            self._DBConnect = Data[9] ## This is the reference to the DBConnect function.

        ## Initialize _TrainedAI Dictionary
        self._TrainedAI = dict()
        for AIType in self._AITypeArray:
            self._TrainedAI[AIType] = dict()

    def TrainAI (self, RealTime):
        print("Training AI....\nSuccessPercentage: {}".format(self._PercentageChange))
        ## GradientData Sproc only needs to be called once. Create a flag for it ##
        MinimumTimeStamp = int((self._CurrentTimeStamp - self._TrainingHours*3600*1e6))

        ## Construct Indicator Data ##
        # Bug in Pymysql requires reconnecting to DB
        db = self._DBConnect()
        cursor = db.cursor()
        #cursor.execute("")
        cursor.callproc("IndicatorData", (MinimumTimeStamp, self._CurrentTimeStamp))
        TrainingData = numpy.asarray(cursor.fetchall())
        cursor.close()
        db.close()
        ## The gradient data is ordered by timestamp. So values will match with outcomes. (Hopefully)
        #Remove the timestamp from the training Data. Used in testing and debugging mainly.
        TrainingData = numpy.delete(TrainingData, 0,1)

        VirtualTimeStamp = self._CurrentTimeStamp
        for SuccessPeriodMins in self._SuccessPeriodMinsList:
            ## Load Database  ##
            db = self._DBConnect()
            ## Obtain Training Set
            cursor = db.cursor()
            if RealTime:
                VirtualTimeStamp = int(self._CurrentTimeStamp - SuccessPeriodMins*60*1e6)

            cursor.callproc("TestSet", (MinimumTimeStamp, VirtualTimeStamp,SuccessPeriodMins, self._PercentageChange))
            Data = cursor.fetchall()
            cursor.nextset()
            TrainingGoal = numpy.asarray(Data)
            cursor.close()
            db.close()
            FittingData = TrainingData

            ## Only use the training data for the useful time period
            if RealTime:
                Difference = len(TrainingData) - len(TrainingGoal)
                FittingData = TrainingData[Difference:len(TrainingData)]

            ## Teach the SVM ##
            if max(TrainingGoal[:,1]) == 0 and min(TrainingGoal[:,1]) == 0: ## No real data in the set.
                continue

            for AIType in self._AITypeArray:
                TrainedAI = self.BuildAI(AIType).fit(FittingData, TrainingGoal[:,1])
                self._TrainedAI[AIType][SuccessPeriodMins] = TrainedAI
            print(SuccessPeriodMins)

        print("Completed Training")
    ## Test AI Alogrithm over a dataset

    def TestAI (self,TestPeriod,Debug):
        # TestPeriod: The SuccessPeriod time to compare to

        #Main Variables
        Predictions = dict()
        #Loop over the success period list to find true results and Prediction data
        #before finding calculating the averages.

        ## Obtain Gradient Data for TestSet ##
        ## Re-open DB due to pymysql bug ##
        db = self._DBConnect()
        cursor = db.cursor()
        cursor.callproc("IndicatorData", (self._TestMinStamp, self._TestMaxStamp))
        IndicatorData = numpy.asarray(cursor.fetchall())
        cursor.close()
        db.close()

        for AIType in self._AITypeArray:
            Predictions[AIType] = dict()
            for SuccessPeriod in self._TrainedAI[AIType].keys(): #These are the success periods
                PredictionDict = dict()
                ## Loop through the data to find predictions ##
                for DataSet in IndicatorData:
                    PredictionDict[int(DataSet[0])] = self._TrainedAI[AIType][SuccessPeriod].predict(numpy.delete(DataSet, 0))[0]
                Predictions[AIType][SuccessPeriod] = PredictionDict

        ## Connect to the Database ##
        # Must do this multiple times due to bug. Should change to mysqldb
        # module
        db = self._DBConnect()

        ## Obtain True Results ##
        cursor = db.cursor()
        cursor.callproc("TestSet", (self._TestMinStamp,  self._TestMaxStamp, TestPeriod, self._PercentageChange))
        Outcomes = numpy.asarray(cursor.fetchall())
        cursor.close()
        db.close()
        ## Calculate the results ##
        Results = dict()
        if Debug:
            APArray = dict()


        for AIType in self._AITypeArray:

            NonZeroCount = 0

            Results[AIType] = {"Matches":0, "Non0":0}
            #Store Average Predictions if in debug mode
            if Debug:
                APArray[AIType]  =  dict()
            for Outcome in Outcomes:
                AveragePrediction = 0
                ItemCount = 0
                for SuccessPeriod in Predictions[AIType].keys():
                    AveragePrediction += Predictions[AIType][SuccessPeriod][int(Outcome[0])]
                    ItemCount += 1
                AveragePrediction = AveragePrediction/ItemCount
                #Store AverageData if in debug mode
                if Debug:
                    APArray[AIType][Outcome[0]] = AveragePrediction

                ## Calculate Results ##
                EffectivePrediction = 0
                if AveragePrediction > self._AcceptanceThreshold:
                    EffectivePrediction = 1
                elif AveragePrediction < -self._AcceptanceThreshold:
                    EffectivePrediction = -1

                if EffectivePrediction == Outcome[1]:
                    if Outcome[1] != 0:
                        Results[AIType]["Non0"] += 1
                    Results[AIType]["Matches"] += 1
                if Outcome[1] != 0:
                    NonZeroCount += 1

            Results[AIType]["Matches"] /= len(Outcomes)
            if NonZeroCount != 0:
                Results[AIType]["Non0"] /= NonZeroCount
            else:
                Results[AIType]["Non0"] = 0

        if Debug:
            return (APArray,Outcomes, Results)
        else:
            return Results

    ## Predicts results for TimeStamp
    def Predict(self, TimeStamp, AIKey):
        # TimeStamp - CurrentTimeStamp to predict
        # AIKey     - the Key for the AI Algorithm used to predict the results
        ## Returns Prediction (-1,0,1) and the average without the threshold

        ## Obtain the Data ##
        db = self._DBConnect()
        cursor = db.cursor()
        cursor.callproc("IndicatorData", (TimeStamp, TimeStamp))
        IndicatorData = numpy.asarray(cursor.fetchall())
        cursor.close()
        db.close()

        Prediction = 0
        PredictionCount = 0
        for SuccessPeriod in self._TrainedAI[AIKey].keys(): #These are the success periods
                Prediction += self._TrainedAI[AIKey][SuccessPeriod].predict(numpy.delete(IndicatorData, 0))[0]
                PredictionCount += 1

        Prediction = Prediction/PredictionCount     # Intentionally give error if this is 0

        if abs(Prediction) < self._AcceptanceThreshold:
            RefinedResult = 0
        elif Prediction >= self._AcceptanceThreshold:
            RefinedResult = 1
        elif Prediction <= -self._AcceptanceThreshold:
            RefinedResult = -1

        return (RefinedResult, Prediction)

