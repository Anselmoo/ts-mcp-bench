w=np.linalg.eigvalsh(build(662,516,3500));w-=w[0]
print(np.round(w[::2]).astype(int))
