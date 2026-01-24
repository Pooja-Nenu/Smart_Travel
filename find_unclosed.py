filepath = 'templates/trip_detail.html'
with open(filepath, 'r') as f:
    content = f.read()

import re
tags = re.findall(r'{% (if|endif|else|elif) .*?%}', content)

stack = []
for i, tag in enumerate(tags):
    if tag == 'if':
        stack.append(i)
    elif tag == 'endif':
        if not stack:
            print(f"Error: endif without if at index {i}")
        else:
            stack.pop()
    # else and elif don't change stack depth

if stack:
    print(f"Error: {len(stack)} unclosed if tags at indices: {stack}")
    for idx in stack:
        # Print some context around the tag
        tag_instances = list(re.finditer(r'{% if .*?%}', content))
        if idx < len(tag_instances):
             start = max(0, tag_instances[idx].start() - 50)
             end = min(len(content), tag_instances[idx].end() + 50)
             print(f"Context for index {idx}: ...{content[start:end]}...")
else:
    print("All if tags are closed in my regex check (might have missed some complex ones)")
