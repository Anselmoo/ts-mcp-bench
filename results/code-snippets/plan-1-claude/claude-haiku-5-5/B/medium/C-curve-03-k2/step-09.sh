
cd /tmp/tsbench-run-me24kyq4 && cat > run.py <<'EOF'
exec(open('ts.py').read())
import numpy as np
V=Vtab(1.0,3699/784)
def levels(Dq):
    P=proj(Dq)
    S,H=build(7,V,P)
    nup=np.array([sum(1 for i in s if so[i][1]>0) for s in S])
    out={}
    for n in (5,4):
        sel=np.where(nup==n)[0]
        out[n]=np.sort(np.linalg.eigvalsh(H[np.ix_(sel,sel)]).real)
    return out
import sys
for Dq in [0.001,1.45,2.45,3.00]:
    o=levels(Dq)
    q=o[5]; d=o[4]
    # remove quartets from Ms=1/2
    dl=list(d)
    for x in q:
        i=min(range(len(dl)),key=lambda k:abs(dl[k]-x)); dl.pop(i)
    g=q[0]
    print('Dq',Dq,'quartets E/B:',np.round(q-g,4))
    # group doublets
    dl=np.array(dl); groups=[]
    for x in np.sort(dl):
        if groups and abs(x-groups[-1][0])<1e-6: groups[-1][1]+=1
        else: groups.append([x,1])
    print('  doublets:',[(round(a-g,4),c) for a,c in groups])
    # group quartets
    gq=[]
    for x in q:
        if gq and abs(x-gq[-1][0])<1e-6: gq[-1][1]+=1
        else: gq.append([x,1])
    print('  quartets grouped:',[(round(a-g,4),c) for a,c in gq])
EOF
python3 run.py