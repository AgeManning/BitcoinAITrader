#!/usr/bin/python
import os
import sys
os.chdir("../Libraries")
sys.path.append(os.getcwd())
from AI import *
os.chdir("../AI")


if __name__ == "__main__":
    #Parameters

    CurrentTimeStamp = 1368905109928145
    SuccessPeriodMinsList = range(5,125,10)
    TrainingHours = 40
    PercentageChange = 2
    ## Testing Parameters
    TestMinStamp = 1368905109928145
    TestMaxStamp = 1368925736124273
    TestPercentageChange = 2
    TestAcceptanceThreshold = 0.4
    AITypeArray = ["SVM", "RandomForest"]
    Data = (CurrentTimeStamp, SuccessPeriodMinsList, TrainingHours, PercentageChange, TestMinStamp, TestMaxStamp, TestPercentageChange, TestAcceptanceThreshold, AITypeArray)

    AIObject = AI(Data)
    AIObject.TrainAI(True)

    (APArray,Outcomes,Results) = AIObject.TestAI(90,True)

    for Outcome in Outcomes:
        print (str(Outcome[0]) + "     :" + str(APArray["RandomForest"][Outcome[0]]) + ":" + str(Outcome[1]))

    import pdb; pdb.set_trace()  # XXX BREAKPOINT




