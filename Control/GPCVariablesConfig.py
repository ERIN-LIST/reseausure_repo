
GPC_Stations = {'KAHe':'KAHe',
                'U1110':'West',
                'U1120':'South',
                'U1141':'North',
                'U1142':'East',
                }

GPC_VarsSpec = { 'U1110':
                 [ 
                   {'OPC':"U_1110_1_010_M_F01_Mes_Skal",'GPC':"Qov"},
                   {'OPC':"U_1110_1_010_M_F01_Zahl",'GPC':"Vov"},
                   {'OPC':"U_1110_1_020_M_L01_Mes_Skal",'GPC':"Lb"},
                   {'OPC':"U_1110_2_010_M_F01_Mes_Skal",'GPC':"Qout"},
                   {'OPC':"U_1110_2_010_M_F01_Zahl",'GPC':"VoutLR"},
                   {'OPC':"U_1110_2_010_M_F01_GPC_Zahl",'GPC':"Vout"},
                   {'OPC':"U_1110_2_010_M_OG01_Mes",'GPC':"Valve"},
                   {'OPC':"U_1110_01_003_P_Ist_Par01_Skal",'GPC':"Qmaintenance"},
                  ],
                 'U1120':
                 [ 
                   {'OPC':"U_1120_1_010_M_L01_Mes_Skal",'GPC':"Lb"},
                   {'OPC':"U_1120_1_020_M_F01_Mes_Skal",'GPC':"Qout"},
                   {'OPC':"U_1120_1_020_M_F01_Zahl",'GPC':"VoutLR"},
                   {'OPC':"U_1120_1_020_M_F01_GPC_Zahl",'GPC':"Vout"},
                  ],
                 'U1141':
                 [ 
                   {'OPC':"U_1141_1_010_M_F01_Mes_Skal",'GPC':"Qov"},
                   {'OPC':"U_1141_1_010_M_F01_Zahl",'GPC':"Vov"},
                   {'OPC':"U_1141_3_020_M_OG01_Mes",'GPC':"Valve"},
                   {'OPC':"U_1141_3_010_M_L01_Mes_Skal",'GPC':"Lb"},
                   {'OPC':"U_1141_3_020_M_F01_Mes_Skal",'GPC':"Qout"},
                   {'OPC':"U_1141_3_020_M_F01_Zahl",'GPC':"VoutLR"},
                   {'OPC':"U_1141_3_020_M_F01_GPC_Zahl",'GPC':"Vout"},
                   {'OPC':"U_1141_01_002_P_Ist_Par01_Skal",'GPC':"Qmaintenance"},
                  ],
                 'U1142':
                 [ 
                   {'OPC':"U_1142_1_010_M_L01_Mes_Skal",'GPC':"Lov"},
                   {'OPC':"U_1142_1_010_M_F01_Mes_Skal",'GPC':"Qov"},
                   {'OPC':"U_1142_1_010_M_F01_Zahl",'GPC':"Vov"},
                   {'OPC':"U_1142_2_010_M_L01_Mes_Skal",'GPC':"Lb"},
                   {'OPC':"U_1142_3_010_M_F01_Mes_Skal",'GPC':"Qout"},
                   {'OPC':"U_1142_3_010_M_F01_Zahl",'GPC':"VoutLR"},
                   {'OPC':"U_1142_3_010_M_F01_GPC_Zahl",'GPC':"Vout"},
                   {'OPC':"U_1142_01_001_P_Ist_Par01_Skal",'GPC':"hPon"},
                   {'OPC':"U_1142_01_001_P_Ist_Par02_Skal",'GPC':"hPoff"},
                   {'OPC':"U_1142_01_001_P_Ist_Par03_Skal",'GPC':"Qmaintenance"},
                  ],
                }

GPCOutVars = {'U1110':
              [ {'OPC':'U_1110_2_010_M_F01_GPC_Bef','GPC':"QoutTrig",'Access':'rw'},
                {'OPC':'U_1110_2_010_M_F01_GPC_Ist','GPC':"QoutSpA"},
                {'OPC':'U_1110_2_010_M_F01_GPC_Soll','GPC':"QoutSpN",'Access':'rw'},
                {'OPC':'U_1110_GPC_Mode_Bef_GPC','GPC':"GPCOnTrig",'Access':'rw'},
                {'OPC':'U_1110_GPC_Mode_Bef_Lokal','GPC':"GPCOffTrig",'Access':'rw'},
                ],
               'U1141':
              [ {'OPC':'U_1141_3_020_M_F01_GPC_Bef','GPC':"QoutTrig",'Access':'rw'},
                {'OPC':'U_1141_3_020_M_F01_GPC_Ist','GPC':"QoutSpA"},
                {'OPC':'U_1141_3_020_M_F01_GPC_Soll','GPC':"QoutSpN",'Access':'rw'},
                {'OPC':'U_1141_GPC_Mode_Bef_GPC','GPC':"GPCOnTrig",'Access':'rw'},
                {'OPC':'U_1141_GPC_Mode_Bef_Lokal','GPC':"GPCOffTrig",'Access':'rw'},
                ],
               'U1142':
              [ {'OPC':'U_1142_3_010_M_F01_GPC_Bef','GPC':"QoutTrig",'Access':'rw'},
                {'OPC':'U_1142_3_010_M_F01_GPC_Ist','GPC':"QoutSpA"},
                {'OPC':'U_1142_3_010_M_F01_GPC_Soll','GPC':"QoutSpN",'Access':'rw'},
                {'OPC':'U_1142_GPC_Mode_Bef_GPC','GPC':"GPCOnTrig",'Access':'rw'},
                {'OPC':'U_1142_GPC_Mode_Bef_Lokal','GPC':"GPCOffTrig",'Access':'rw'},
                ],
               }

GPCStateVars = {'U1110':
               [ 
                 {'OPC':"U_1110_01_SPS_Ist_Minute",'GPC':"LifeM"},
                 {'OPC':"U_1110_01_SPS_Ist_Stunde",'GPC':"LifeH"},
                 {'OPC':"U_1110_GPC_Alive",'GPC':"GPCLife",'Access':'rw'},
                 {'OPC':'U_1110_GPC_Mode_Ist','GPC':"GPCState"},
                ],
               'U1120':
               [
                 {'OPC':"U_1120_01_SPS_Ist_Minute",'GPC':"LifeM"},
                 {'OPC':"U_1120_01_SPS_Ist_Stunde",'GPC':"LifeH"},
               ],
               'U1140':
               [ 
                 {'OPC':"U_1140_01_SPS_Ist_Minute",'GPC':"LifeM"},
                 {'OPC':"U_1140_01_SPS_Ist_Stunde",'GPC':"LifeH"},
                 {'OPC':"U_1140_GPC_Alive",'GPC':"GPCLife",'Access':'rw'},
                 {'OPC':'U_1140_GPC_Mode_Ist','GPC':"GPCState"},
                ],
               'U1141':
               [ 
                 {'OPC':"U_1141_01_SPS_Ist_Minute",'GPC':"LifeM"},
                 {'OPC':"U_1141_01_SPS_Ist_Stunde",'GPC':"LifeH"},
                 {'OPC':"U_1141_GPC_Alive",'GPC':"GPCLife",'Access':'rw'},
                 {'OPC':'U_1141_GPC_Mode_Ist','GPC':"GPCState"},
                ],
               'KaHe_FWZ':
               [ 
                 {'OPC':"KA_He_05_GPC_Alive",'GPC':"GPCLife",'Access':'rw'},
                ],
               }

OPCVarSpecif = {}
for si,varsi in GPCOutVars.iteritems(): # Find another loop over all listed Variable specifications
    for vi in varsi:
        if vi.get('Access','') == 'rw':
            OPCVarSpecif[':.'.join([si,vi['OPC']])] = vi
for si,varsi in GPCStateVars.iteritems():
    for vi in varsi:
        if vi.get('Access','') == 'rw':
            OPCVarSpecif[':.'.join([si,vi['OPC']])] = vi
