cat > p.py <<'E'
import pickle,numpy as np,json
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
res=pickle.load(open('res.pkl','rb'))
for d,l in res: print(d,[(round(float(e),3),t) for e,t in l[:6]])
# plot: need finer grid -> reuse module
exec(open('t.py').read().split("res=[]")[0])
xs=np.linspace(0,4,41);curves=[]
for Dq in xs:
    H=build(Dq*B);w=np.linalg.eigvalsh(H);curves.append(w)
E
python3 p.py