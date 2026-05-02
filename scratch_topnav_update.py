import os, glob

search_dir = r'c:\Users\USER\OneDrive\Documents\the crown dashboard\templates'
files = glob.glob(os.path.join(search_dir, '*.html'))

find_str = '''                        {% if is_master %}
                            <a href="/admin/motions" class="text-xs font-bold text-emerald-400 hover:text-emerald-300 bg-emerald-900/30 px-3 py-1 rounded border border-emerald-700/50 transition-colors uppercase tracking-widest leading-none flex items-center">Motions</a>
'''
replace_str = '''                        <a href="/admin/motions" class="text-xs font-bold text-emerald-400 hover:text-emerald-300 bg-emerald-900/30 px-3 py-1 rounded border border-emerald-700/50 transition-colors uppercase tracking-widest leading-none flex items-center">Motions</a>
                        {% if is_master %}
'''

# But some files have a slight variation depending on spaces or lines.
# Instead of literal match, I will read the file line by line and move the line containing "/admin/motions" to be strictly above "{% if is_master %}" only if it is currently inside it.

count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if '{% if is_master %}' in content and '/admin/motions' in content:
        # A safer dynamic regex approach using python
        import re
        
        # Regex to match: {% if is_master %} followed by optional spaces/newlines, then the motions link
        pattern = r'({%\s*if is_master\s*%})\s*(<a href="/admin/motions"[^>]*>Motions</a>)'
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, r'\2\n                        \1', content)
            if new_content != content:
                with open(f, 'w', encoding='utf-8') as file:
                    file.write(new_content)
                count += 1
                print('Updated:', f)
        else:
            # Also check if it's already moved or formatted differently
            # In index.html, it's slightly different
            pass

print('Total updated with topnav replace:', count)
