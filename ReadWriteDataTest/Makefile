#################################################################
# Macros.
#

SM_SOURCES=     GPCAlgGlobFSM.sm
SOURCES=        $(SM_SOURCES:%.sm=%_sm.py)
MAIN=    python GPCAlgGlobFSM.py

#export PYTHONPATH=../../../lib/Python

# Uncomment to turn on debug message generation.
TRACE=          -g

# Uncomment to turn on reflection.
# REFLECT=        -reflect
SMCRoot = D:\Project-work\soft\SmcSrc_6_1_0\smc
SMC=            java -jar $(SMCRoot)\bin\Smc.jar
SMC_FLAGS=      -python $(TRACE) $(REFLECT)

RM_F=           del /f

#################################################################
# Rules.
#

%_sm.py :       %.sm
		$(SMC) $(SMC_FLAGS) $<

%_sm.dot :      %.sm
		$(SMC) -graph -glevel 1 $<

%_sm.png :      %_sm.dot
		dot -T png -o $@ $<

%_sm.svg :      %_sm.dot
		dot -T svg -o $@ $<

%_sm.html :     %.sm
		$(SMC) -table $<

all :           GPCAlgGlobFSM svg png

GPCAlgGlobFSM :   $(SOURCES)

test:
		-$(MAIN)

graph :         $(SM_SOURCES:%.sm=%_sm.dot)

png :           $(SM_SOURCES:%.sm=%_sm.png)

svg :           $(SM_SOURCES:%.sm=%_sm.svg)

table :         $(SM_SOURCES:%.sm=%_sm.html)

clean :
		-$(RM_F) *_sm.py
		-$(RM_F) *.pyc
		-$(RM_F) *_sm.dot
		-$(RM_F) *_sm.png
		-$(RM_F) *_sm.svg
		-$(RM_F) *_sm.html
