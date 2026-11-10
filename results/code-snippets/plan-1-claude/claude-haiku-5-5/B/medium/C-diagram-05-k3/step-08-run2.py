exec(open('run.py').read().split('# Dq=0 analysis')[0])
H0 = Hee
for key,(Bfull,d) in blocks.items():
    Hb = Bfull.T @ H0 @ Bfull
    Lb = Bfull.T @ L2 @ Bfull
    # simultaneous diag: H + 1e-3 L2 ; L2 and H commute
    w, v = np.linalg.eigh(Hb + 1e-3*Lb)
    out=[]
    for k in range(0,len(w),d):
        vk = v[:,k:k+d]
        Hk = (vk.T@Hb@vk); Lk = (vk.T@Lb@vk)
        out.append((round(np.linalg.eigvalsh(Hk)[0],4), round(np.linalg.eigvalsh(Lk)[0],3), round(np.linalg.eigvalsh(Lk)[-1],3)))
    print(key, d, out)
