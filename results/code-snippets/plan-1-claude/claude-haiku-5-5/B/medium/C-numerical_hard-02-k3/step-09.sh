cat > scan.py << 'EOF'
import numpy as np
HFt=np.load('HFt.npy'); HDt=np.load('HDt.npy')
obs=np.array([22900,23730,24580.])
def levels(x):
    e=np.linalg.eigvalsh(HFt+x*HDt)
    e=e-e[0]
    # unique levels with multiplicity divisible by 3 (triplet components)
    out=[];i=0
    while i<len(e):
        j=i
        while j<len(e) and abs(e[j]-e[i])<1e-6: j+=1
        if j-i>0 and e[i]>1e-6: out.append((e[i],j-i))
        i=j
    return out
res=[]
for x in np.arange(0.3,6.0,0.0025):
    L=levels(x)
    L=[v for v,m in L if m%3==0 and v<20]  # placeholder
    if len(L)<3: continue
    L=np.array(L)
    # try assign obs to 3 levels a<b<c (indices) with B scaling: E_obs = B*L
    # ratios: (Eb-Ea)/(Ec-Ea) = 830/1680
    for i in range(len(L)):
        for j in range(i+1,len(L)):
            for k in range(j+1,len(L)):
                r=(L[j]-L[i])/(L[k]-L[i])
                res.append((abs(r-830/1680),x,i,j,k,r))
res.sort()
for r in res[:15]: print(r)
EOF
python3 scan.py