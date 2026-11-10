from fit import levels
import sys
Dq,B,C=map(float,sys.argv[1:4])
Esx,cl=levels(Dq,B,C)
for e,d in cl: print(round(e,1),d)
