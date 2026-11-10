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
