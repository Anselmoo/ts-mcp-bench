from t import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
for dq in (0.005,):
    print([(f"{m}{names.get((o,c),(o,c))}",round((e-levels(dq)[0][0])/B,3)) for e,m,o,c in levels(dq)[:12]])
xs=np.linspace(0,4,81);Y=[]
for x in xs:
    o=levels(x);e0=o[0][0];Y.append([((e-e0)/B) for e,*_ in o[:12]])
Y=np.array(Y)
# plot relative to ground (levels sorted by energy; crossings show as kinks)
plt.figure(figsize=(7,6))
for i in range(Y.shape[1]): plt.plot(xs,Y[:,i],lw=1)
plt.xlabel("Dq/B");plt.ylabel("E/B");plt.ylim(0,60);plt.title("d7 Tanabe-Sugano (B=859, C=3660)")
plt.savefig("diagram.png",dpi=120)
