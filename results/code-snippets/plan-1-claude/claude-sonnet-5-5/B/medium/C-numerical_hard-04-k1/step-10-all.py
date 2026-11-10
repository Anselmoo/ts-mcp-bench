print("refine")
def fit(Dq0,B0):
    bestc=(1e18,)
    for Dq in np.arange(Dq0-100,Dq0+101,10):
        for B in np.arange(B0-50,B0+51,5):
            l=np.array(lv(Dq,B));c=np.sum((l[:3]-t)**2)
            if c<bestc[0]: bestc=(c,Dq,B,l)
    return bestc
print(fit(3300,630)); print(fit(3400,900))
