cat > scan2.py << 'EOF'
import numpy as np
exec(open('scan.py').read().split('res=[]')[0])
def levels_m(x):
    e=np.linalg.eigvalsh(HFt+x*HDt); e=e-e[0]
    out=[];i=0
    while i<len(e):
        j=i
        while j<len(e) and abs(e[j]-e[i])<1e-6: j+=1
        if e[i]>1e-6: out.append((e[i],j-i))
        i=j
    return out
best=[]
for x in np.arange(0.3,6.0,0.0025):
    L=levels_m(x)
    # lowest-first list of triplet levels with orbital degeneracy (mult/3)
    Lt=[(v,m//3) for v,m in L][:8]
    # candidate: three triplet T-levels (deg 3) among first 8 levels
    T=[v for v,d in Lt if d==3]
    for i in range(len(T)):
        for j in range(i+1,len(T)):
            for k in range(j+1,len(T)):
                r=(T[j]-T[i])/(T[k]-T[i])
                best.append((abs(r-830/1680),round(x,4),T[i],T[j],T[k]))
best.sort()
for b in best[:10]: print(b)
EOF
python3 scan2.py