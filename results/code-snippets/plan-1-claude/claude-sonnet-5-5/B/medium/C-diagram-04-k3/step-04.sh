cat >> t.py <<'E'
import json
json.dump({str(k):[(a,float(b)) for a,b in v[:6]] for k,v in allr.items()},open('res.json','w'))
try:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    xs=np.linspace(0,4,41);Y=[]
    for x in xs:
        H=H2+max(x,1e-5)*H1;w=np.linalg.eigvalsh((H+H.T)/2);Y.append(w-w[0])
    Y=np.array(Y)
    for k in range(Y.shape[1]): plt.plot(xs,Y[:,k],lw=.6)
    plt.ylim(0,60);plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png',dpi=120)
    print('saved')
except Exception as e: print(e)
E
python3 t.py >/dev/null; python3 -c "
import json;print(json.load(open('res.json'))['0.0'])"; sha256sum diagram.png; realpath diagram.png