import numpy as np, irr
for Dq in [0,800,1743,2500]:
    print("Dq",Dq)
    for row in irr.analyze(Dq,780,3500):
        if row[0]=='D' and row[1]<30000:
            print("   ",row[1],row[2],row[3])
