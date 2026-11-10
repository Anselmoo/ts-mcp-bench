cd <SANDBOX_TMP>/ts && cat > run3.py << 'EOF'
exec(open('run.py').read().split('# Dq=0 analysis')[0])
def block_spectrum(dq, want_L=True):
    H = dq*Hcf + Hee
    res = {}
    for key,(Bfull,d) in blocks.items():
        Hb = Bfull.T @ H @ Bfull
        Lb = Bfull.T @ L2 @ Bfull
        w, v = np.linalg.eigh(Hb)
        levs = []
        for k in range(0,len(w),d):
            vk = v[:,k:k+d]
            # L2 expectation on the cluster
            Lk = np.linalg.eigvalsh(vk.T@Lb@vk)
            levs.append((w[k], Lk))
        res[key]=levs
    return res
if __name__=='__main__':
    for eps in [1e-6]:
        sp = block_spectrum(eps)
        for key,levs in sp.items():
            print(key, [(round(e,6), np.round(L,3).tolist()) for e,L in levs])
EOF
python3 run3.py