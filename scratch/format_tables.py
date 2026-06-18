import re

with open('專題報告.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
table_count = 1
in_table = False

for i, line in enumerate(lines):
    if line.strip().startswith('|'):
        if not in_table:
            in_table = True
            
            # Find the line immediately before the table that has text
            prev_idx = len(out_lines) - 1
            while prev_idx >= 0 and out_lines[prev_idx].strip() == '':
                prev_idx -= 1
                
            if prev_idx >= 0:
                prev_line = out_lines[prev_idx].strip()
                # Check if it already has a table caption
                if re.match(r'^表\s*\d+[:：\s]*', prev_line):
                    caption = re.sub(r'^表\s*\d+[:：\s]*', '', prev_line).strip()
                    if not caption: caption = '表格說明'
                    out_lines[prev_idx] = f'**表 {table_count}：{caption}**\n'
                elif prev_line.endswith('：') or prev_line.endswith(':'):
                    # It's an introductory sentence ending with a colon
                    out_lines.append(f'\n**表 {table_count}：{prev_line.rstrip("：:")}**\n')
                else:
                    # It's a regular sentence or a header
                    # We just append a generic caption if it's a markdown header
                    if prev_line.startswith('#'):
                        out_lines.append(f'\n**表 {table_count}：{prev_line.lstrip("# ").strip()}**\n')
                    else:
                        out_lines.append(f'\n**表 {table_count}：{prev_line}**\n')
            else:
                out_lines.append(f'\n**表 {table_count}：表格說明**\n')
                
            table_count += 1
            
        out_lines.append(line)
    else:
        in_table = False
        out_lines.append(line)

with open('專題報告.md', 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print('Done. Updated', table_count - 1, 'tables.')
