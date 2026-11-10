cat > run_d6.py << 'EOF'
import sys
sys.argv = ['x', '6']
exec(open('ts.py').read())
res = {}
for Dq in np.arange(0, 4.01, 0.5):
    lv = analyze(Dq)
    E0 = lv[0][0]
    res[Dq] = [(e-E0, S, nm) for e, S, nm in lv]
    print('Dq/B = %.1f  (Dq=%.1f)' % (Dq, Dq))
    for e, S, nm in res[Dq][:14]:
        print('   %10.5f  S=%.0f  %s' % (e, S, nm))
EOF
time python3 run_d6.py 2>/dev/null