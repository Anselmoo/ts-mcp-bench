export MPLCONFIGDIR=/tmp/mpl; cat > run.py <<'EOF'
import numpy as np, json
H0=np.load('H0.npy');Hv=np.load('Hv.npy');Ms=np.load('Ms.npy');Ml=np.load('Ml.npy')
B=828.
ph=np.exp(-1j*Ml*np.pi/2)
def levels(x):
    w,v=np.linalg.eigh(H0+Hv*x*B)
    w=w/B; out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-6: j+=1
        V=v[:,i:j]; deg=j-i
        S=max(abs(m) for m in set(Ms) if (np.abs(V[Ms==m])**2).sum()>1e-6)
        mult=int(2*S+1); dim=deg//mult
        chi=np.real((np.abs(V)**2*ph[:,None]).sum())/mult
        lab={1:{1:'A1g',-1:'A2g'},2:{0:'Eg'},3:{1:'T1g',-1:'T2g'}}[dim][int(round(chi))]
        out.append([w[i],f"{mult}{lab}",deg]);i=j
    return out
eps=1e-4
res=[];curves={}
for k in range(9):
    x=0.5*k; L=levels(x if x>0 else eps)
    # ordinal labels for repeated symmetries
    cnt={};lab=[]
    for e,t,d in L:
        cnt[t]=cnt.get(t,0)+1; lab.append((e,t,cnt[t]))
    g=lab[0][0]
    res.append((x,[(t+(f"({n})" if n>1 or sum(1 for q in lab if q[1]==t)>1 else ""),round(e-g,3)) for e,t,n in lab[:6]]))
for r in res: print(r)
xs=np.linspace(eps,4,161);import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
data={}
for x in xs:
    L=levels(x);g=L[0][0];cnt={}
    for e,t,d in L:
        cnt[t]=cnt.get(t,0)+1; data.setdefault((t,cnt[t]),[]).append((x,e-g))
plt.figure(figsize=(8,8))
for (t,n),p in data.items():
    p=np.array(p);plt.plot(p[:,0],p[:,1],'-' if t[0]=='4' else '--',lw=1)
    if len(p)==len(xs) and p[-1,1]<80: plt.text(4.02,p[-1,1],f"$^{t[0]}${t[1:]}",fontsize=7)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d3 Oh, C/B=%.3f'%(3390/828));plt.ylim(0,80);plt.xlim(0,4.4)
plt.savefig('diagram.png',dpi=120)
EOF
python3 run.py; sha256sum diagram.png; pwd