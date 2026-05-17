with open('pricing-v2.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """html += '<button class=\"pricing-cta ' + btnClass + '\" onclick=\"openOrderModal(\\'' + key + '\\')\">' + ctaText + '</button>';"""

new = """html += '<button class=\"pricing-cta ' + btnClass + '\" onclick=\"location.href=\\'checkout.html?plan=' + key + '\\'\">' + ctaText + '</button>';"""

if old in content:
    content = content.replace(old, new)
    with open('pricing-v2.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: replaced")
else:
    print("FAIL: old pattern not found")
    import re
    matches = list(re.finditer(r"html\s*\+=.*pricing-cta.*btnClass", content))
    for m in matches:
        start = max(0, m.start() - 20)
        end = min(len(content), m.end() + 80)
        snippet = content[start:end]
        print(f"Found near: {repr(snippet)}")
