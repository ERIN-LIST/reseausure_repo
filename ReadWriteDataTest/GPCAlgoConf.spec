[Global]
OPCServer = string()
tUpdateDefault = integer(60, 900, default=600)

[GPCLife]
minSampling = integer(7, 600, default=7)
toBlank = boolean(default=False)
pctGPCSamp = integer(1, 100, default=1)

[MPC]
simu = boolean(default=True)
simuMode = option('OPCWrite', 'NoOPCWrite', 'NoOPCWriteTrigger', 'OPCReadOnly')
logFile = string()
mode = option('Opti', 'Dummy')

[MPC_Opti]
ControlTimeperiod = integer(60, 900, default=600)
SolverVerbos = integer(0, 2, default=0)

  [[ParamOptiProb]]
  YRef = integer(20,180) # < MaxWWTP
  MaxWWTP = integer(20,250) 

  [[CostFunctionWeights]]
  VolumeHomogenity = integer(0,10, default=1)
  HomogenityHorizonProfile = option('Constant', 'Linear', default='Constant')
  NetworkOutflowRef = integer(0,10, default=1)
  OverflowMin = integer(0,10, default=5)
  OvSensitivity = boolean(default=False)

[MPC_Dummy]
