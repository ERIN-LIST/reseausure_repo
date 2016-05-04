""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
import win32pdh, re, win32api

def procinfo(InfoItems=['ID Process',], filter=re.compile('.*')):
    #each instance is a process, you can have multiple processes w/same name
    junk, instances = win32pdh.EnumObjectItems(None,None,'process', win32pdh.PERF_DETAIL_WIZARD)
    proc_Info={}
    proc_dict={}
    for instance in instances:
        if not filter.match(instance): continue
        if instance in proc_dict:
            proc_dict[instance] = proc_dict[instance] + 1
        else:
            proc_dict[instance]=0
    for instance, max_instances in proc_dict.items():
        for inum in xrange(max_instances+1):
            instancei = '%s (%s)'%(instance,inum)
            hq = win32pdh.OpenQuery() # initializes the query handle
            for IItem in InfoItems:
                if IItem not in junk: continue
                path = win32pdh.MakeCounterPath( (None,'process',instance, None, inum,IItem) )
                counter_handle=win32pdh.AddCounter(hq, path)
                win32pdh.CollectQueryData(hq) #collects data for the counter
                type, val = win32pdh.GetFormattedCounterValue(counter_handle, win32pdh.PDH_FMT_LONG)
                try:
                    proc_Info[instancei][IItem] = str(val)
                except KeyError:
                    proc_Info[instancei] = {IItem: str(val)}

            win32pdh.CloseQuery(hq)

    #proc_Info.sort()
    return proc_Info


print procinfo(InfoItems=['ID Process','Private Bytes','Virtual Bytes','Elapsed Time'],
               filter=re.compile('python|CODESY'))
