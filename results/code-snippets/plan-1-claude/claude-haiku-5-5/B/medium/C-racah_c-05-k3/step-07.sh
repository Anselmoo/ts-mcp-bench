
cat << 'EOF' > fit.py
import numpy as np, itertools
exec(open('d3b.py').read().split('def spectrum')[0])
sub=lambda M: M[np.ix_(idx,idx)]
Ocf=np.zeros((dim,dim)); O2=np.zeros((dim,dim)); O4=np.zeros((dim,dim))
eps=[-4,-4,-4,6,6]
for o in range(5):
    for s in range(2):
        p=2*o+s; Ocf+=eps[o]*CR[p]@AN[p]
for a,b,c,d in itertools.product(range(5),repeat=4):
    v2=A2[a,c,b,d]; v4=A4[a,c,b,d]
    if abs(v2)<1e-13 and abs(v4)<1e-13: continue
    for s1 in range(2):
        for s2 in range(2):
            p=2*a+s1; q=2*b+s2; r=2*d+s2; s=2*c+s1
            T=0.5*CR[p]@CR[q]@AN[r]@AN[s]
            O2+=v2*T; O4+=v4*T
Ocf,O2,O4=sub(Ocf),sub(O2),sub(O4)
S2e,S2v=np.linalg.eigh(S2full)
def levels(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    H=Dq*Ocf+F2*O2+F4*O4
    out=[]
    for sv in [0.75,3.75]:
        Vs=S2v[:,np.abs(S2e-sv)<1e-6]
        es=np.sort(np.linalg.eigvalsh(Vs.T@H@Vs))
        # group
        groups=[]
        for e in es:
            if groups and abs(e-groups[-1][0])<0.5: groups[-1][1]+=1
            else: groups.append([e,1])
        out.append((sv,groups))
    return out
if __name__=="__main__":
    for sv,g in levels(1750.,600.,2400.):
        print(sv,[(round(e-0,1),m) for e,m in g])
EOF
python3 fit.py
