# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 09:26:40 2019

@author: shosborn
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 08:53:41 2019

@author: shosborn
"""

from gurobipy import *
from random import random, gauss, uniform, choice
import pandas as pd

class Baseline_sched:
    #create variables for frame sizes
    
    def __init__(self, taskSystem):
        self.solver=Model("qcp")
        self.taskSystem=taskSystem
        
    #print("Testing if arguments work.")
    #print(taskSystem.allTasks[1].allCosts[5])
    
    def setSolverParams(self):
        taskSystem=self.taskSystem
        self.solver.setParam("TimeLimit", taskSystem.timeout)
        self.solver.setParam(GRB.Param.Threads, taskSystem.threadsPerTest)
        self.solver.setParam("SolutionLimit", taskSystem.solutionLimit)
        #For fastest peformance, set lb=ub=1
        self.inverseSpeed=self.solver.addVar(lb=taskSystem.lowerBound, ub=taskSystem.upperBound, vtype=GRB.CONTINUOUS)
        self.solver.setObjective(self.inverseSpeed, GRB.MAXIMIZE)
    
    def schedule(self):
        self.setSolverParams()
        self.frameSize=self.solver.addVar(lb=self.taskSystem.periodMin, ub=self.taskSystem.hyperperiod, vtype=GRB.INTEGER)
        self.createSchedVars()
        self.allJobsScheduled()
        self.noFrameOverloaded()
        #self.jobsPinnedToCore()
        self.jobsNotParallel()
        self.solver.optimize()
        return self.solver.getAttr(GRB.Attr.Status)
        #self.printFrameSizes()
        #print("Effective util:")
        #print(self.effectiveUtil())

             
    def printFrameSizes(self):
        print("Printing frame sizes.")
        for i in range(1, self.taskSystem.m+1):
            print(self.frameSize[i].x)


    def createSchedVars(self):
        taskSystem=self.taskSystem
        self.schedVars={'taskID_1'      : [],
                        'jobID_1'       : [],
                        'coreID'        : [],
                        'frameID'       : [],
                        'schedVarCont'  : [],
                        'schedVarBin'   : []
                }

        for i in range(taskSystem.nTotal):
            #print("i=", i)
            task1=taskSystem.allTasks[i]
            period=task1.period
            
            for a in range(1, (int) (taskSystem.hyperperiod/period)+1):
                #print("Creating solo variable")
                #print("a=", a)
                release=(a-1)*period
                deadline=a*period
                self.job_var(i, a, release, deadline, period)        
        self.schedVarsP=pd.DataFrame(self.schedVars)
        
        
    def job_var(self, task, job, release, deadline, period):
        taskSystem=self.taskSystem
        for coreID in range (1, taskSystem.m+1):
            for frameID in range (1, taskSystem.hyperperiod+1):
                #print("coreID", coreID, "frameID", frameID)
                self.schedVars['taskID_1'].append(task)
                self.schedVars['jobID_1'].append(job)
                self.schedVars['coreID'].append(coreID)
                self.schedVars['frameID'].append(frameID)

                #continuous variable allows for preemptive execution
                var1C=(self.solver.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS))
                self.schedVars['schedVarCont'].append(var1C)       

                var1B=(self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY))
                self.schedVars['schedVarBin'].append(var1B)
                #var1B is true if var1C>0
                self.solver.addConstr(var1B >= var1C)
                
                self.solver.addConstr(deadline >= var1B * self.frameSize*frameID)
                self.solver.addConstr(var1B * release <=self.frameSize*(frameID-1))
                '''
                frame does not have to divide the hyperperiod, but if it does not,
                nothing can be scheduled in the last frame that would break the HP
                and we reset at the end, i.e. the last frame per HP is short.
                If anything is scheduled in the frame, it ends no later than
                the HP.
                '''
                self.solver.addConstr(var1B*self.frameSize*frameID <= taskSystem.hyperperiod)
            
   
    def allJobsScheduled (self):
        taskSystem=self.taskSystem
        for i in range(taskSystem.nTotal):
            task1=taskSystem.allTasks[i]
            period1=task1.period
            for a in range(1, (int)(taskSystem.hyperperiod/period1+1)):
                schedVarsThisJob=self.schedVarsP[(self.schedVarsP['taskID_1']==i ) & (self.schedVarsP['jobID_1']==a)]
                #CONSTRAINT: all jobs must be scheduled
                exprC = LinExpr()
                exprB = LinExpr()
                for k in range(len(schedVarsThisJob.index)):
                    #iterate over all variables coresponding to job (i, a)
                    exprC += schedVarsThisJob['schedVarCont'].iloc[k]
                    exprB += schedVarsThisJob['schedVarBin'].iloc[k]
                self.solver.addConstr(lhs=exprC, rhs=1, sense=GRB.EQUAL)
                #will be greater than 1 if job is preempted
                self.solver.addConstr(lhs=exprB, rhs=1, sense=GRB.GREATER_EQUAL)
    
    
    def jobsNotParallel(self):
        taskSystem=self.taskSystem
        for i in range(taskSystem.nTotal):
            task1=taskSystem.allTasks[i]
            period1=task1.period
            for a in range(1, int(taskSystem.hyperperiod/period1+1)):
                #check that job is scheduled on at most one core per frame
                for frameID in range(1, taskSystem.hyperperiod+1):
                    schedVarsThisJobThisFrame=self.schedVarsP[(self.schedVarsP['taskID_1']==i ) & 
                                                              (self.schedVarsP['jobID_1']==a) &
                                                              (self.schedVarsP['frameID']==frameID)]
                    expr=LinExpr()
                    for k in range(len(schedVarsThisJobThisFrame.index)):
                        expr+=schedVarsThisJobThisFrame['schedVarBin'].iloc[k]
                    #parallel=self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    #expr needs to be at most 1
                    self.solver.addConstr(lhs=expr, rhs=1, sense=GRB.LESS_EQUAL)
    
    '''
    #Jim doesn't like this requirement
    #replaced with jobsNotParallel
    def jobsPinnedToCore(self):
        taskSystem=self.taskSystem
        m=taskSystem.m
        for coreID in range(1, m+1):
            for i in range(taskSystem.nTotal):
                task1=taskSystem.allTasks[i]
                period1=task1.period
                for a in range(1, (int)(taskSystem.hyperperiod/period1+1)):
                    schedVars=self.schedVarsP[(self.schedVarsP['coreID']==coreID) & (self.schedVarsP['taskID_1']==i ) & (self.schedVarsP['jobID_1']==a)]
                    expr=LinExpr()
                    pinned=self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    for k in range(len(schedVars.index)):
                        expr+=schedVars['schedVarCont'].iloc[k]
                    #either all or none of this job is on current core
                    self.solver.addConstr(lhs=expr, rhs=pinned, sense=GRB.EQUAL)
    '''
 
    def noFrameOverloaded(self):
        taskSystem=self.taskSystem
        m=taskSystem.m
        for coreID in range (1, m+1):
            for frameID in range(1, taskSystem.hyperperiod+1):
                schedVarsThisFrame=self.schedVarsP[(self.schedVarsP['coreID']==coreID ) & (self.schedVarsP['frameID']==frameID)]        
                expr=LinExpr()
                for k in range(len(schedVarsThisFrame.index)):
                    task1=schedVarsThisFrame['taskID_1'].iloc[k]
                    var=schedVarsThisFrame['schedVarCont'].iloc[k]
                    cost=taskSystem.allTasks[task1].cost
                    expr += var*cost*self.inverseSpeed
                    # end for for k loop
                self.solver.addConstr(expr <= self.frameSize)
