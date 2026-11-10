def f(x):
    e=tr(x); return [e[1]-16474,e[4]-25381]
s=fsolve(f,[2000,600]); print(s, f(s))
e=tr(s); print(np.round(e[:8]))
