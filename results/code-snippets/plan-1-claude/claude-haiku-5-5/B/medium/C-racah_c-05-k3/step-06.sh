
sed -i 's/R=np.einsum(.ikp,pq->ikq.,rho_w,P)/R=np.einsum("ikp,pq->ikq",rho_w,P)/; s/return np.einsum(.ikq,jlq->ikjl.,R,rho)/return np.einsum("ikq,jlq->ikjl",R,rho_w)/' d3b.py && python3 d3b.py
