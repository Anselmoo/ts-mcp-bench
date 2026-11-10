cd /tmp/tsbench-run-l39pr0fd; cat >> run2.py <<'E'
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,81); E_=[]
for x in xs:
    r=lv(x); e0=r[0][0]; E_.append([((e-e0)/B,l_) for e,l_,d in sorted(r,key=lambda t:t[0])[:12]])
plt.figure(figsize=(7,8))
# plot lowest 6 levels by rank, colored by label at each point
for k in range(6):
    plt.plot(xs,[E_[i][k][0] for i in range(len(xs))],'.-',ms=3,label=f'level {k+1}')
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d5 Tanabe-Sugano (B=806, C=3570 cm$^{-1}$), lowest 6 levels');plt.legend()
plt.savefig('diagram.png',dpi=120)
E
python3 run2.py >/dev/null 2>&1; sha256sum diagram.png; realpath diagram.png