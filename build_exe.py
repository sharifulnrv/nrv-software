import PyInstaller.__main__
import os
import shutil
import certifi

# Clean up previous build
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# Define PyInstaller arguments
# Get certifi pem path
cert_path =  os.path.join(os.path.dirname(certifi.__file__), 'cacert.pem')

args = [
    'run_gui.py',  # Entry point
    '--name=NexusRiverView',
    '--onefile',  # Single executable
    '--noconsole', # Hide console
    # Add data files: source;dest
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--add-data=admin_config.json;.',
    '--add-data=nexus-river-view-600x866.ico;.', 
    f'--add-data={cert_path};certifi', # Explicitly add certifi bundle
    # Hidden imports
    '--hidden-import=engineio.async_drivers.threading',
    '--hidden-import=certifi', 
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=openpyxl.cell._writer',
    '--hidden-import=webview',
    '--hidden-import=tkinter',
    '--hidden-import=filedialog',
    # Icon if available
    '--icon=nexus-river-view-600x866.ico',
    '--clean',
]

print("Building EXE with arguments:", args)
PyInstaller.__main__.run(args)

print("Build complete. detailed logs in build/ and output in dist/")
