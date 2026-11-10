from fit2 import *
for Dq,B,C in [(0,1,0),(0,0,1),(1000,0,0),(1000,0,1)]:
    eq,ed=levels(Dq,B,C)
    print(Dq,B,C,"Q",[(round(e-eq.min(),3),m) for e,m in clusters(eq)])
    print("   D",[(round(e-eq.min(),3),m) for e,m in clusters(ed)])
