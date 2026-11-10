cat >> p.py <<'E'
fig=plt.figure(figsize=(6,6))
for w in [0]:pass
C_=np.array([np.unique(np.round(w-w[0],6)) for w in curves],dtype=object)
for i,(x,w) in enumerate(zip(xs,curves)):
    u=np.unique(np.round(w,4));g=u[0]
    plt.plot([x]*8,(u[:8]-g)/B,'k.',ms=3)
plt.xlabel('Dq/B');plt.ylabel('E/B (above lowest level at each Dq/B)');plt.title('d5 octahedral levels, C/B=%.2f'%(C/B))
plt.savefig('diagram.png',dpi=120)
E
python3 p.py >/dev/null 2>&1; sha256sum diagram.png; pwd