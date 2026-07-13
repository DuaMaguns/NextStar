import sys
import os
print('cwd:', os.getcwd(), flush=True)
print('before import', flush=True)
try:
    import app
    print('app imported', flush=True)
    print('Flask app object:', app.app, flush=True)
    print('Starting server...', flush=True)
    app.app.run(host='0.0.0.0', port=5000, debug=False)
except Exception as e:
    print('ERROR:', e, flush=True)
    import traceback
    traceback.print_exc()
