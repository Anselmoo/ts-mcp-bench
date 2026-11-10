import time
exec(open('/dev/shm/d5/d5.py').read())
t=time.time()
for Dq in [1.45,2.55,3.25]:
    res=levels(Dq)
    g=[r for r in res if abs(r[0]-2.5)<1e-9]
    E0=min(r[2] for r in g)
    print("Dq",Dq, "ground", g[0] if g else None, "E0",E0)
    ex=sorted([(r[2]-E0,r[0],r[1]) for r in res if r[2]-E0>1e-6])
    # merge duplicates
    out=[]
    for e,S,n in ex:
        if out and abs(out[-1][0]-e)<1e-5: continue
        out.append((e,S,n))
    for e,S,n in out[:6]:
        print("  E/B=%.4f  mult=%d  %s"%(e,int(2*S+1),n))
print(time.time()-t)
