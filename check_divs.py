import re

with open("channels_integration/templates/channels/channel_list.html", encoding="utf-8") as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines, start=1):
    opens = len(re.findall(r"<div\b", line))
    closes = len(re.findall(r"</div>", line))
    for _ in range(opens):
        stack.append(i)
    for _ in range(closes):
        if stack:
            stack.pop()

print(f"Unclosed <div> tags remaining: {len(stack)}")
print("Line numbers where these unclosed divs were opened:")
for line_num in stack:
    print(f"  Line {line_num}: {lines[line_num-1].strip()}")