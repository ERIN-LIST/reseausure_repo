""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
import sys, os

__path__ = ["..",]

curDir = os.path.abspath(os.path.curdir)
for pi in __path__:
    sys.path[0:0] = [os.path.join( curDir, pi),]

GPCConfFile = "GPCAlgoConf.ini"
