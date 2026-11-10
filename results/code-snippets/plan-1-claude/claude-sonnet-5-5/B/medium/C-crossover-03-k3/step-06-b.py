exec(open('a.py').read().split('for D in')[0])
H0,S=build(sel0,0)
w=np.linalg.eigvalsh(H0+1e6*S); print(np.round(w[:40]-np.linalg.eigvalsh(build(sel2,0)[0])[0]))
