import main, numpy as np
cal,_ = main.levels_for(1e-5)
for E,g,Lf,lab in sorted(cal['d'], key=lambda t:t[0]):
    print(round(E,4), g, Lf)
