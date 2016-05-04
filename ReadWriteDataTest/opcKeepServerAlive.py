""" ===================
* Copyright© 2008-2016 LIST (Luxembourg Institute of Science and Technology), all right reserved.
* Authorship : Georges Schutz, David Fiorelli, 
* Licensed under GPLV3
=================== """
import OpenOPC
from time import sleep
import config
from handleConfig import readGPCConfig


def main():
    c,cval = readGPCConfig(config.GPCConfFile)
    opc = OpenOPC.client()
    opc.connect(c["Global"]["OPCServer"])
    while True:
        print [xi for xi in opc.info() if xi[0] == 'Current Time']
        print "OPC-Server alive: %s" % opc.ping()
        #print opc.read('??') ToTest: need to get an info from all Sations?
        sleep(2)

if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            sleep(10)
