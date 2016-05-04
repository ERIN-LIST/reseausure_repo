""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """

if __name__ == '__main__':
    import config

from Control.GPCVariablesConfig import GPCOutVars

variables = {'OPC_Group':'GPCTriggerReset' }
for sti in GPCOutVars:
    variables[sti] = [vi for vi in GPCOutVars[sti] if vi['GPC'].endswith('Trig')]

from ReadNeededDataTest.ReadData_useOPC import AlgData_OPC
OPCServer = "OPCManager.DA.XML-DA.Server.DA" #{"CoDeSys.OPC.02", "OPCManager.DA.XML-DA.Server.DA"}
TrigOPC = AlgData_OPC(variables = variables, opcserver = OPCServer)
TrigOPC.readOPC()

for vti in TrigOPC.opcVarsDict:
    TrigOPC.opcVarsDict[vti].setWriteValue(0)

WStatus = TrigOPC.writeOPC(allStored=True, toOPC=True)
print WStatus
