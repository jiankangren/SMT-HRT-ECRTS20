'''
Communicate to outside:
    total util.
    util of just-added task.
    result of test:  success/ fail/ timeout.
Need to add tasks individually to system.
Have seperate methods for CERT-MT, multi-frame no SMT, baseline.
'''

import CERTMT_sched as cert
#import npCERTMT_sched as np
import baseline_sched as base
#import MultiFrameNoSMT_sched as multi
#import OneFrameSizeSMT_sched as oneFrame
#import fullPreemption2_sched as fullPreempt

from gurobipy import *
from random import random, gauss, uniform, choice
from numpy.random import lognormal
import pandas as pd


UNIFORM=1
SPLIT_UNIFORM=2
NORMAL=3
SPLIT_NORMAL=4

BASELINE=1
#Preemptive CE scheduler
CERT_MT=2
#multiple frames, non-SMT tasks are preemptable
FAIL=3


    
        

#create task system
class CERTMT_TaskSystem:
          #test=TaskSet(targetUtil, utilMin, utilMax, periodMin, periodCount, symMean, symDev, symDistrib, m, timeout, solutionLimit, lowerBound, upperBound)
    def __init__(self, targetUtil, utilMin, utilMax, periodMin, periodCount, symParam1, symParam2, symParam3, symDistrib, m, timeout, solutionLimit, lowerBound, upperBound, threadsPerTest):
        

        #will be used by solvers
        self.timeout=timeout
        self.solutionLimit=solutionLimit
        self.lowerBound=lowerBound
        self.upperBound=upperBound
        
        self.targetUtil = targetUtil
        self.utilMin=utilMin
        self.utilMax=utilMax
        self.periodMin = periodMin
        self.periodCount = periodCount
        self.symParam1=symParam1
        self.symParam2=symParam2
        self.symParam3=symParam3
        self.symDistrib=symDistrib
        self.m=m

        #how many threads should the solver use per test?
        #if not set, will take all available threads.
        #This will make individual tests run faster, but probably harmful overall,
        #since we're also trying to parallelize the graphs.
        self.threadsPerTest=threadsPerTest
        
        
        self.hyperperiod=periodMin*2**(periodCount-1)
        self.periods=[]

        
        
        #print("Creating periods")
        for i in range(periodCount):
            self.periods.append(periodMin*(2**i))
            #print(self.periods[i])
        self.allTasks = []
        self.totalUtil = 0


        while self.totalUtil < targetUtil:
            self.addTask()   
        
        self.assignPairCosts()

    def addTask(self):
        #tasks are zero-indexed
        self.nTotal = permID = len(self.allTasks)
        util = uniform(self.utilMin, self.utilMax)
        period = choice(self.periods)
        #print("New task period", period)
        task = SmartTask(util, period, permID)
        self.allTasks.append(task)
        self.totalUtil = self.totalUtil + util
        #print("current total util=", self.totalUtil)
        self.nTotal += 1
        
    def addTaskAndUpdateCosts(self):
        self.addTask()
        #update pair costs for the new task
        
        #not needed for baseline only
        newTaskID=self.nTotal-1
        newTask=self.allTasks[newTaskID]
        for i in range(newTaskID):
            maxCost=max(self.allTasks[i].cost, self.allTasks[newTaskID].cost)
            minCost=min(self.allTasks[i].cost, self.allTasks[newTaskID].cost)
            if maxCost > minCost*10:
                #don't want to use SMT in this case
                costToHide=10
            else:
                costToHide=self.setCostToHide()
            pairCost=maxCost+minCost*costToHide
            #pairCost=symbiosis*min(self.allTasks[i].cost, self.allTasks[newTaskID].cost) + max(self.allTasks[i].cost, self.allTasks[newTaskID].cost)
            newTask.allCosts.append(pairCost)
            self.allTasks[i].allCosts.append(pairCost)
        #add own cost to task
        newTask.allCosts.append(newTask.cost)
        
    
    
    def testSystem(self, runBaseline, runCertMT):
        if runBaseline:
            if self.totalUtil>self.m:
                successBaseline=False
            else:
                baseline=base.Baseline_sched(self)
                successBaseline=(baseline.schedule()==GRB.OPTIMAL)
        else: 
            successBaseline=False
        
        if runCertMT:
            '''
            if partition:
                twoSystems=self.partition()
                sched1=cert.certMT_sched(twoSystems[0])
                sched2=cert.certMT_sched(twoSystems[2])
                successCertMT=(sched1.schedule()==GRB.OPTIMAL and sched2.schedule()==GRB.OPTIMAL)
            '''    
            certMT=cert.certMT_sched(self)
            successCertMT=(certMT.schedule()==GRB.OPTIMAL)
            '''
            if successCertMT:
                print()
                self.printTaskSystem()
                certMT.printSolution()
                print()
            '''
                
        else:
            successCertMT=False
        
        #the negative one is there to help with indexing
        return -1, successBaseline, successCertMT


    def assignPairCosts(self):
        for i in range(self.nTotal):
            self.allTasks[i].allCosts=[]
            for j in range(self.nTotal):
                self.allTasks[i].allCosts.append(0)
        
        for i in range(self.nTotal):
            for j in range(self.nTotal):
                if i==j:
                    self.allTasks[i].allCosts[j]=self.allTasks[j].cost
                else:
                    maxCost=max(self.allTasks[i].cost, self.allTasks[j].cost)
                    minCost=min(self.allTasks[i].cost, self.allTasks[j].cost)
                    if maxCost>minCost*10:
                        #don't use threading
                        costToHide=10
                    else:
                        costToHide=self.setCostToHide()
                    pairCost=maxCost+costToHide*minCost
                    self.allTasks[i].allCosts[j]=pairCost
                    self.allTasks[j].allCosts[i]=pairCost
                    
    def setCostToHide(self):
        if self.symDistrib==UNIFORM:
            costToHide=uniform(self.symParam1, self.symParam2)
        elif self.symDistrib==SPLIT_UNIFORM:
            whichRange=random()
            if whichRange<self.symParam3:
                #no threading here
                costToHide=10
            else:
                costToHide=uniform(self.symParam1, self.symParam2)
        elif self.symDistrib==NORMAL:
            #don't want values <=0
            costToHide=min(0.01, gauss(self.symParam1, self.symParam2))
        elif self.symDistrib==SPLIT_NORMAL:
            whichRange=random()
            if whichRange<self.symParam3:
                #no threading here
                costToHide=10
            else:
                costToHide=min(0.01, gauss(self.symParam1, self.symParam2))
        return costToHide
    
    
    
    
    def printTaskSystem(self):
        print("totalUtil: ", self.totalUtil)
        for i in range(self.nTotal):
            task=self.allTasks[i]
            print(i, "period:", task.period, "cost:", task.cost, "otherCosts:", task.allCosts)


    
class SmartTask:

    def __init__(self, util, period, permID):
        self.util = float(util)
        self.period = period
        self.cost = util * period
        self.permID = permID
        self.allCosts=[]


'''
    def __str__(self):
        return "τ{0}: ({1:0.2f}U, {2:0.0f}T, {3})".format(self.permID, self.util, self.period, str(self.symAdj))

    def __repr__(self):
        return self.__str__()
'''


'''
targetUtil=4
utilMin=.1
utilMax=1
periodMin=1
periodCount=4
symMean=.5
symDev=.1
symDistrib=NORMAL
m=4
timeout=60
solutionLimit=100
lowerBound=1
upperBound=1
test=CERTMT_TaskSystem(targetUtil, utilMin, utilMax, periodMin, periodCount, symMean, symDev, symDistrib, m, timeout, solutionLimit, lowerBound, upperBound)
test.testSystem()
'''
