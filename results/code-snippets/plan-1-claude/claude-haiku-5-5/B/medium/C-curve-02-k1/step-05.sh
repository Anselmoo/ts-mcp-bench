
cd /tmp/tsbench-run-s2tzcfyu && python3 -c "
from d3 import run
for xd in [1.0,2.2,3.5]:
    q,d=run(xd)
    g=q[0][0]
    quart=[(e-g,n,c,'Q') for e,n,c in q[1:]]
    # remove quartet energies from doublet list
    dl=[(e,n,c) for e,n,c in d]
    for e,n,c in q:
        for i,(ee,nn,cc) in enumerate(dl):
            if abs(ee-e)<1e-6 and nn>=n:
                dl[i]=(ee,nn-n,cc); break
    dd=[(ee-g,nn,cc) for ee,nn,cc in dl if nn>0 and abs(ee-g)>1e-6]
    print(xd, 'quartets', [(round(a,4),b,c) for a,b,c,_ in quart])
    print('  doublets', [(round(a,4),b,c) for a,b,c in dd[:4]])
"
