exec(open('d5.py').read().split('for Dq in')[0])
for Dq in [1.45,2.55,3.25]:
    res=levels(Dq)
    allE=sorted(res,key=lambda r:r[2])
    E0=allE[0][2]
    print("Dq",Dq,"global ground:",allE[0][0],allE[0][1],"E0=",E0, " sextet A1 at", [r[2]-E0 for r in res if abs(r[0]-2.5)<1e-9])
    out=[]
    for S,n,v in allE:
        e=v-E0
        if e<1e-6: continue
        if out and abs(out[-1][0]-e)<1e-5: continue
        out.append((e,S,n))
    for e,S,n in out[:6]:
        print("   E/B=%.4f  %s%s  (S=%g)"%(e,int(2*S+1),n,S))
