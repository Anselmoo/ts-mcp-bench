python3 -c "
import numpy as np, itertools
import d7
src=open('d7.py').read()
src=src.replace('combinations(range(NSO),7)','combinations(range(NSO),NE)')
src=src.replace('def build(Dq,B,C):','def build(Dq,B,C,NE=7):')
exec(src)
for NE in (2,3):
    H,S2=build(0,100,0,NE)
    w,v=np.linalg.eigh(H+1e5*S2)
    res={}
    for vec in v.T:
        s2=vec@S2@vec; S=(-1+np.sqrt(1+4*s2))/2
        key=(round(S*2)/2, round(vec@H@vec,3))
        res[key]=res.get(key,0)+1
    print(NE, sorted(res.items()))
"