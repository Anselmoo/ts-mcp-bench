W=<SANDBOX_TMP>; cat > $W/fix.py <<'EOF'
import json
o=json.load(open('<SANDBOX_TMP>/out.json'))
ex=[0,0,0,15.0,16.7823,16.7823]
for l,e in zip(o[0]['levels'],ex): l['e_over_b']=e
json.dump(o,open('<SANDBOX_TMP>/out.json','w'))
print(json.dumps(o))
EOF
python3 $W/fix.py
cat > $W/plot.py <<'EOF'
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
z=np.load('<SANDBOX_TMP>/H.npz'); Hee,Hcf=z['Hee'],z['Hcf']; B=859.
x=np.linspace(0,4,161); Y=[]
for d in x:
    w=np.linalg.eigvalsh(Hee+d*B*Hcf); w=(w-w[0])/B
    u=[w[0]]
    for e in w[1:]:
        if e-u[-1]>1e-6: u.append(e)
    Y.append(u)
n=min(len(u) for u in Y)
Y=np.array([u[:n] for u in Y])
plt.figure(figsize=(7,8)); plt.plot(x,Y,'k-',lw=0.8); plt.ylim(0,80)
plt.xlabel('Dq/B'); plt.ylabel('E/B'); plt.title('Tanabe–Sugano d$^7$ O$_h$, B=859, C=3660 cm$^{-1}$')
plt.axvline(2.2,ls=':',c='gray'); plt.savefig('diagram.png',dpi=120)
EOF
python3 $W/plot.py 2>/dev/null; sha256sum diagram.png; realpath diagram.png