
cd $TMPDIR && sed -i 's/least_squares(res,\[2500,700\])/least_squares(res,[2500,700],diff_step=1e-3)/' fit.py && python3 fit.py
