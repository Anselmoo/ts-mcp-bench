exec(open('fit2.py').read())
best=None
for F2g in [30000,40000,50000]:
  for F4g in [15000,25000]:
    for Dqg in [1800,2000]:
        try:
            r=least_squares(resid,[Dqg,F2g,F4g],xtol=1e-12,ftol=1e-12,gtol=1e-12)
        except Exception as ex:
            continue
        if best is None or r.cost<best.cost: best=r
p=best.x; print("fit Dq,F2,F4 =",p,"cost",best.cost,"resid(cm-1 /1000)",best.fun)
Dq,F2,F4=p
B=(9*F2-5*F4)/441; C=35*F4/441
print("Dq=%.1f B=%.1f C=%.1f C/B=%.3f"%(Dq,B,C,C/B))
print(energies(p))
