from ts import *
import json
Lname='SPDFGHI'
r0=solve(0.0); e0=r0[0][0]
terms=[]  # (energy, mult, L)
for e,m,g in r0:
    n=len([1]) 
# degeneracy from mods list length -> (2L+1) since Ms=0 block contains one copy per L multiplet
for e,m,g in r0:
    L=(len(eval(g))-1)//2 if g.startswith('[') else 0 if g=='A1' else 1
    terms.append((e,m,L))
rt=solve(1e-6)
cnt={}; parent={}
for e,m,g in rt:
    t=min(terms,key=lambda t:abs(t[0]-e)+(0 if t[1]==m else 1e9))
    k=(m,g); cnt[k]=cnt.get(k,0)+1
    parent[(m,g,cnt[k])]=(f"{m}{Lname[t[2]]}",t[0])
def labeled(Dq):
    r=solve(Dq if Dq>0 else 1e-6); c={}; out=[]
    for e,m,g in r:
        k=(m,g); c[k]=c.get(k,0)+1
        p,ef=parent[(m,g,c[k])]
        out.append([ef if Dq==0 else e, f"{m}{g}g({p})"])
    out.sort(); g0=out[0][0]
    return [(lab,e-g0) for e,lab in out]
allres={}
for i in range(0,81):
    dq=i*0.05; allres[round(dq,2)]=labeled(dq)
json.dump({str(k):v for k,v in allres.items()},open('all.json','w'))
for i in range(9):
    dq=i*0.5
    print(dq,[(l,round(e,4)) for l,e in allres[dq][:7]])
