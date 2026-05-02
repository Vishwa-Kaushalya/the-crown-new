import os, glob, re

search_dir = r'c:\Users\USER\OneDrive\Documents\the crown dashboard\templates'
files = glob.glob(os.path.join(search_dir, '*.html'))

count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # We want to place the Motions Vault link right after 'Admin Mode</span>'
    # But only if it's not already there
    
    # Regex pattern to match Admin Mode span
    pattern = r'(<span[^>]*>Admin Mode</span>\s*)'
    
    match = re.search(pattern, content)
    if match:
        # First, strip all existing links pointing to /admin/motions anywhere in the top nav
        # This prevents duplicate injections
        clean_content = re.sub(r'<a href="/admin/motions"[^>]*>.*?</a>\s*', '', content)
        
        replacement = match.group(1) + '<a href="/admin/motions" class="text-[10px] font-bold text-amber-400 hover:text-amber-300 bg-amber-900/30 px-3 py-1 rounded border border-amber-700/50 transition-colors uppercase tracking-widest leading-tight text-center mt-1 flex items-center gap-1">🔐 Vault</a>\n                        '
        new_content = re.sub(pattern, replacement, clean_content, count=1)
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            count += 1
            print('Updated nav in:', f)

print('Total updated top nav:', count)
