import os
import re

def fix_except_pass(directory):
    pattern = re.compile(r'^[ \t]*except[ \t]*([^:]*):[ \t]*\n[ \t]*pass', re.MULTILINE)
    
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if we have except: pass or similar
                if 'except' in content and 'pass' in content:
                    lines = content.split('\n')
                    new_lines = []
                    modified = False
                    
                    for i, line in enumerate(lines):
                        # Match things like "except Exception: pass" or "except: pass" or "except (ValueError, OSError): pass"
                        match = re.search(r'^([ \t]*)except[ \t]*(.*?):[ \t]*pass[ \t]*$', line)
                        if match:
                            indent = match.group(1)
                            exc_type = match.group(2).strip()
                            if not exc_type:
                                exc_type = "Exception"
                            
                            # Replace the line
                            new_line = f"{indent}except {exc_type} as e: logging.getLogger(__name__).error('Fehler: %s', e)"
                            new_lines.append(new_line)
                            modified = True
                        else:
                            # Also check multi-line "except Exception:\n    pass"
                            if line.strip() == "pass" and i > 0 and "except" in lines[i-1] and lines[i-1].strip().endswith(":"):
                                prev_match = re.search(r'^([ \t]*)except[ \t]*(.*?):[ \t]*$', lines[i-1])
                                if prev_match:
                                    indent = prev_match.group(1)
                                    exc_type = prev_match.group(2).strip()
                                    if not exc_type:
                                        exc_type = "Exception"
                                    
                                    # Modify previous line and current line
                                    new_lines[-1] = f"{indent}except {exc_type} as e:"
                                    # Add logging instead of pass, with deeper indent (assume 4 spaces)
                                    new_lines.append(f"{indent}    logging.getLogger(__name__).error('Fehler: %s', e)")
                                    modified = True
                                else:
                                    new_lines.append(line)
                            else:
                                new_lines.append(line)
                                
                    if modified:
                        new_content = '\n'.join(new_lines)
                        if 'import logging' not in new_content:
                            # Insert import logging after the docstring or at the top
                            if new_content.startswith('"""'):
                                end_doc = new_content.find('"""', 3)
                                if end_doc != -1:
                                    new_content = new_content[:end_doc+3] + '\nimport logging\n' + new_content[end_doc+3:]
                                else:
                                    new_content = 'import logging\n' + new_content
                            else:
                                new_content = 'import logging\n' + new_content
                        
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        count += 1
                        print(f"Fixed {path}")

    return count

if __name__ == "__main__":
    count = fix_except_pass("/Users/landjunge/Documents/AG-Flega/src/gnom_hub")
    print(f"Total files modified: {count}")
