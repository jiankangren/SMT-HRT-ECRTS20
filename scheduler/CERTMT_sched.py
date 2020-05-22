# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 08:53:41 2019

@author: shosborn
"""

from gurobipy import *
from random import random, gauss, uniform, choice
import pandas as pd

class certMT_sched:
    #create variables for frame sizes
    
    def __init__(self, taskSystem):
        self.solver=Model("qcp")
        self.taskSystem=taskSystem
        
    #print("Testing if arguments work.")
    #print(taskSystem.allTasks[1].allCosts[5])
    
    def printSolution(self):
        self.printFrameSizes()
        print("taskID_1", "jobID_1", "release1", "deadline1", "soloCost1", 
              "taskID_2", "jobID_2", "release2", "deadline2", "soloCost2",
              "jointCost",
              "coreID", "frameID", "frameSize", "frameStart", "frameEnd",
              "schedVarCont", 
              "schedVarCont*cost")
        allTasks=self.taskSystem.allTasks
        for k in range(len(self.schedVarsP.index)):
            if self.schedVarsP['schedVarCont'].iloc[k].x>0:
                task1=self.schedVarsP['taskID_1'].iloc[k]
                job1=self.schedVarsP['jobID_1'].iloc[k]
                task2=self.schedVarsP['taskID_2'].iloc[k]
                job2=self.schedVarsP['jobID_2'].iloc[k]
                
                coreID=self.schedVarsP['coreID'].iloc[k]
                frameID=self.schedVarsP['frameID'].iloc[k]
                frameSize=self.frameSize[coreID].x
                frameStart=frameSize*(frameID-1)
                frameEnd=frameSize*frameID
                
                
                release1=allTasks[task1].period*(job1-1)
                deadline1=allTasks[task1].period*job1
                release2=allTasks[task2].period*(job2-1)
                deadline2=allTasks[task2].period*job2
                print(task1, job1, release1, deadline1, allTasks[task1].cost,
                      task2, job2, release2, deadline2, allTasks[task2].cost,
                      allTasks[task1].allCosts[task2],
                      coreID, frameID, frameSize, frameStart, frameEnd,
                      self.schedVarsP['schedVarCont'].iloc[k].x,
                      self.schedVarsP['schedVarCont'].iloc[k].x*allTasks[task1].allCosts[task2]
                      )
                
        

        
        '''
        buyx = m.getAttr('x', buy)
        for f in foods:
            if buy[f].x > 0.0001:
                print('%s %g' % (f, buyx[f]))
        '''
    
    def setSolverParams(self):
        taskSystem=self.taskSystem
        self.solver.setParam("TimeLimit", taskSystem.timeout)
        self.solver.setParam("SolutionLimit", taskSystem.solutionLimit)
        self.solver.setParam(GRB.Param.Threads, taskSystem.threadsPerTest)
        #For fastest peformance, set lb=ub=1
        self.inverseSpeed=self.solver.addVar(lb=taskSystem.lowerBound, ub=taskSystem.upperBound, vtype=GRB.CONTINUOUS)
        self.solver.setObjective(self.inverseSpeed, GRB.MAXIMIZE)
    
    def schedule(self):
        self.setSolverParams()
        self.createFrameSizeVars()
        self.createSchedVars()
        self.allJobsScheduled()
        self.noFrameOverloaded()
        self.jobsPinnedToCore()
        self.solver.optimize()
        return self.solver.getAttr(GRB.Attr.Status)
        #self.printFrameSizes()
        #print("Effective util:")
        #print(self.effectiveUtil())
    
    def createFrameSizeVars(self):
        taskSystem=self.taskSystem
        m=taskSystem.m
        hyperperiod=taskSystem.hyperperiod
        #create vars for frame lengths
        self.frameSize=[]
        #appending a zero so we can be 1-indexed
        self.frameSize.append(0)
        for coreID in range(1, m+1):
            #Note: restriction that frame size divides hyperperiod is in job_pair_var()
            frameSizeVar=self.frameSize.append(self.solver.addVar(lb=taskSystem.periodMin, ub=taskSystem.hyperperiod, vtype=GRB.INTEGER))
            #hyperperiod/frameSize must be integer
            #frameQuotient=self.solver.addVar(lb=1, ub=hyperperiod/self.taskSystem.periodMin, vtype=GRB.INTEGER)
            #self.solver.addQConstr(frameSizeVar*frameQuotient=hyperperiod)
            
 
    def printFrameSizes(self):
        print("Printing frame sizes.")
        for i in range(1, self.taskSystem.m+1):
            print(self.frameSize[i].x)
    
    def effectiveUtil(self):
        #sanity check
        taskSystem=self.taskSystem
        totalCost=0
        for k in range(len(self.schedVarsP.index)):
            task1=self.schedVarsP['taskID_1'].iloc[k]
            task2=self.schedVarsP['taskID_2'].iloc[k]
            if task1 >= task2 and (self.schedVarsP['schedVar'].iloc[k]==1):
                #print("Pair used:")
                #print("Task", task1, "job", self.schedVarsP["jobID_1"].iloc[k],"Task", task2, "job", self.schedVarsP["jobID_2"].iloc[k])
                #print("Cost:", taskSystem.allTasks[task1].allCosts[task2])
                totalCost+=taskSystem.allTasks[task1].allCosts[task2]        
        effectiveUtil=totalCost/taskSystem.hyperperiod
        return effectiveUtil


    def createSchedVars(self):
        taskSystem=self.taskSystem
        self.schedVars={'taskID_1'      : [],
                        'jobID_1'       : [],
                        'taskID_2'      : [],
                        'jobID_2'       : [],
                        'coreID'        : [],
                        'frameID'       : [],
                        'schedVarCont'  : [],
                        'schedVarBin'   : []
                }

        for i in range(taskSystem.nTotal):
            task1=taskSystem.allTasks[i]
            period1=task1.period
            for j in range(i, taskSystem.nTotal):
                if i==j:
                    #jobs are one-indexed, as in paper
                    for a in range(1, (int (taskSystem.hyperperiod/period1)+1)):
                        release1=(a-1)*period1
                        deadline1=a*period1
                        self.job_pair_var(i, i, a, a, release1, release1, deadline1, deadline1, period1, period1)
                else:
                    task2=taskSystem.allTasks[j]
                    period2=task2.period
                    for a in range(1, (int (taskSystem.hyperperiod/period1)+1)):
                        release1=(a-1)*period1
                        deadline1=a*period1
                        for b in range(1, (int (taskSystem.hyperperiod/period2)+1)):
                            release2=(b-1)*period2
                            deadline2=b*period2
                            if release1<deadline2 and release2<deadline1:
                                self.job_pair_var(i, j, a, b, release1, release2, deadline1, deadline2,period1, period2)
                #end of else
            #end of j loop
        #end of i loop
        #convert the variables I just put together to a pandas dataframe        
        self.schedVarsP=pd.DataFrame(self.schedVars)
        
        
    def job_pair_var(self, task1, task2, jobA, jobB, release1, release2, deadline1, deadline2, period1, period2):
        taskSystem=self.taskSystem
        for coreID in range (1, taskSystem.m+1):
            for frameID in range (1, taskSystem.hyperperiod+1):
                self.schedVars['taskID_1'].append(task1)
                self.schedVars['taskID_2'].append(task2)
                self.schedVars['jobID_1'].append(jobA)
                self.schedVars['jobID_2'].append(jobB)
                self.schedVars['coreID'].append(coreID)
                self.schedVars['frameID'].append(frameID)
                
                #this is kind of weird
                if task1==task2:
                    var1C=(self.solver.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS))
                    self.schedVars['schedVarCont'].append(var1C)       
                else:
                    var1C=(self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY))
                    self.schedVars['schedVarCont'].append(var1C)
                var1B=(self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY))
                self.schedVars['schedVarBin'].append(var1B)
                self.solver.addConstr(var1B >= var1C)
                    
                
                if task1 != task2:
                    #print("non-solo: adding second variable")
                    self.schedVars['taskID_1'].append(task2)
                    self.schedVars['taskID_2'].append(task1)
                    self.schedVars['jobID_1'].append(jobB)
                    self.schedVars['jobID_2'].append(jobA)
                    self.schedVars['coreID'].append(coreID)
                    self.schedVars['frameID'].append(frameID)
                    var2B=(self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY))
                    #same variable, just shows up twice
                    self.schedVars['schedVarCont'].append(var2B)
                    self.schedVars['schedVarBin'].append(var2B)
                    self.solver.addConstr(var1B == var2B)
                
                self.solver.addConstr(deadline1 >= var1B * self.frameSize[coreID]*frameID)
                self.solver.addConstr(deadline2 >= var1B * self.frameSize[coreID]*frameID)
                self.solver.addConstr(var1B * release1 <=self.frameSize[coreID]*(frameID-1))
                self.solver.addConstr(var1B * release2 <=self.frameSize[coreID]*(frameID-1))
                '''
                frame does not have to divide the hyperperiod, but if it does not,
                nothing can be scheduled in the last frame that would break the HP
                and we reset at the end, i.e. the last frame per HP is short.
                If anything is scheduled in the frame, it ends no later than
                the HP.
                '''
                self.solver.addConstr(var1B*self.frameSize[coreID]*frameID <= taskSystem.hyperperiod)
            
   
    def allJobsScheduled (self):
        taskSystem=self.taskSystem
        for i in range(taskSystem.nTotal):
            task1=taskSystem.allTasks[i]
            period1=task1.period
            for a in range(1, (int(taskSystem.hyperperiod/period1+1))):
                schedVarsThisJob=self.schedVarsP[(self.schedVarsP['taskID_1']==i ) & (self.schedVarsP['jobID_1']==a)]
                #CONSTRAINT: all jobs must be scheduled
                exprC = LinExpr()
                #exprB = LinExpr()
                for k in range(len(schedVarsThisJob.index)):
                    #iterate over all variables coresponding to job (i, a)
                    exprC += schedVarsThisJob['schedVarCont'].iloc[k]
                    #exprB += schedVarsThisJob['schedVarBin'].iloc[k]
                self.solver.addConstr(lhs=exprC, rhs=1, sense=GRB.EQUAL)
                #will be greater than 1 if job is preempted
                #self.solver.addConstr(lhs=exprB, rhs=1, sense=GRB.GREATER_EQUAL)
    
    def jobsPinnedToCore(self):
        taskSystem=self.taskSystem
        m=taskSystem.m
        for coreID in range(1, m+1):
            for i in range(taskSystem.nTotal):
                task1=taskSystem.allTasks[i]
                period1=task1.period
                for a in range(1, (int(taskSystem.hyperperiod/period1+1))):
                    schedVars=self.schedVarsP[(self.schedVarsP['coreID']==coreID) & (self.schedVarsP['taskID_1']==i ) & (self.schedVarsP['jobID_1']==a)]
                    expr=LinExpr()
                    pinned=self.solver.addVar(lb=0, ub=1, vtype=GRB.BINARY)
                    for k in range(len(schedVars.index)):
                        #how much of the job is associated with this variable?
                        expr+=schedVars['schedVarCont'].iloc[k]
                    #either all or none of this job is on current core
                    self.solver.addConstr(lhs=expr, rhs=pinned, sense=GRB.EQUAL)
 
    def noFrameOverloaded(self):
        taskSystem=self.taskSystem
        m=taskSystem.m
        for coreID in range (1, m+1):
            for frameID in range(1, taskSystem.hyperperiod+1):
                schedVarsThisFrame=self.schedVarsP[(self.schedVarsP['coreID']==coreID ) & (self.schedVarsP['frameID']==frameID)]        
                expr=LinExpr()
                for k in range(len(schedVarsThisFrame.index)):
                    task1=schedVarsThisFrame['taskID_1'].iloc[k]
                    task2=schedVarsThisFrame['taskID_2'].iloc[k]
                    #inequality avoids double-counting jobs
                    if task1 >= task2:
                        var=schedVarsThisFrame['schedVarCont'].iloc[k]
                        cost=taskSystem.allTasks[task1].allCosts[task2]
                        #expr += var*cost
                        expr += var*cost*self.inverseSpeed
                    # end for for k loop
                self.solver.addConstr(expr <= self.frameSize[coreID])
