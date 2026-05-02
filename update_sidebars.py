import glob
import os

target = """<div class="p-6 flex flex-col gap-6 mt-4">
            <a href="/timer\""""

replacement = """<div class="p-6 flex flex-col gap-6 mt-4">
            {% if is_admin %}
            <a href="/admin/registration" class="text-blue-400 hover:text-blue-300 text-sm font-bold uppercase tracking-wider transition-colors flex items-center gap-3">
                📋 Registration
            </a>
            {% endif %}
            <a href="/timer\""""

for file in glob.glob('templates/*.html'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if target in content:
        content = content.replace(target, replacement)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated sidebar in {file}')

# Also clean up the top navbar in admin_registration.html where I added it
nav_target = """<a href="/admin/registration" class="text-xs font-bold text-blue-400 hover:text-blue-300 bg-blue-900/30 px-3 py-1 rounded border border-blue-700/50 transition-colors uppercase tracking-widest leading-none flex items-center shadow-lg shadow-blue-900/20">Registration</a>"""
nav_replacement = ""

with open('templates/admin_registration.html', 'r', encoding='utf-8') as f:
    content = f.read()
if nav_target in content:
    content = content.replace(nav_target, nav_replacement)
    with open('templates/admin_registration.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Removed from top navbar in admin_registration.html")
    
# Clean it up from templates/index.html just in case I pasted it there? Wait, I only added it to admin_registration.html's navbar.

