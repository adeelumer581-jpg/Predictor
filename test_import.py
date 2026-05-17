import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Don't set RENDER, so async_mode stays None for local testing
import web_ui
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'index.html')
print(f'index.html exists: {os.path.exists(path)}')
if os.path.exists(path):
    print(f'index.html size: {os.path.getsize(path)} bytes')
    with open(path, 'r') as f:
        print('First 100 chars:', f.read(100))
print('Import OK')
