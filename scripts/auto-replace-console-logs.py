#!/usr/bin/env python3
"""
Automated Console.log to Logger Migration Script
Intelligently replaces console.log with appropriate logger calls
"""

import re
import os
from pathlib import Path

FRONTEND_SRC = Path("/home/daihungpham/__projects__/4genthub/agenthub-frontend/src")

def has_logger_import(content: str) -> bool:
    """Check if file already imports logger"""
    return bool(re.search(r'^import\s+logger\s+from\s+[\'"].*logger', content, re.MULTILINE))

def get_relative_logger_path(file_path: Path) -> str:
    """Calculate relative path to logger from given file"""
    rel = os.path.relpath(FRONTEND_SRC / "utils/logger.ts", file_path.parent)
    # Convert to import path
    rel = rel.replace(os.sep, '/').replace('.ts', '')
    if not rel.startswith('.'):
        rel = './' + rel
    return rel

def add_logger_import(content: str, file_path: Path) -> str:
    """Add logger import after existing imports"""
    logger_path = get_relative_logger_path(file_path)

    # Find the last import statement
    import_pattern = r'^import\s+.*?;?\s*$'
    imports = list(re.finditer(import_pattern, content, re.MULTILINE))

    if imports:
        last_import = imports[-1]
        insert_pos = last_import.end()
        return content[:insert_pos] + f"\nimport logger from '{logger_path}';" + content[insert_pos:]
    else:
        # No imports found, add at the beginning
        return f"import logger from '{logger_path}';\n" + content

def determine_log_level(console_stmt: str) -> str:
    """Determine appropriate logger level based on context"""
    lower = console_stmt.lower()

    if 'error' in lower or 'failed' in lower or '❌' in console_stmt or '⚠️' in console_stmt:
        return 'error'
    elif 'warn' in lower or 'warning' in lower:
        return 'warn'
    elif 'debug' in lower or '🎬' in console_stmt or '🔍' in console_stmt:
        return 'debug'
    else:
        return 'debug'  # Default to debug for most logs

def extract_filename(file_path: Path) -> str:
    """Extract just the filename for the filepath parameter"""
    return file_path.name

def replace_console_log(match: re.Match, file_path: Path) -> str:
    """Replace a single console.log statement"""
    full_match = match.group(0)
    args = match.group(1)

    # Determine log level
    level = determine_log_level(full_match)

    # Parse arguments - handle single string vs multiple args
    # Simple heuristic: if contains comma not in quotes/objects, it has multiple args

    # Check if it's a simple string or has data object
    if args.strip().startswith('"') or args.strip().startswith("'") or args.strip().startswith('`'):
        # Simple string message
        filename = extract_filename(file_path)
        return f"logger.{level}({args}, {{}}, '{filename}')"
    else:
        # Has data object or multiple arguments
        # Try to split on first comma outside of braces/quotes
        parts = split_console_args(args)

        if len(parts) == 1:
            # Single argument (probably string)
            filename = extract_filename(file_path)
            return f"logger.{level}({parts[0]}, {{}}, '{filename}')"
        else:
            # Multiple arguments - first is message, rest is data
            message = parts[0].strip()
            data = ', '.join(parts[1:]).strip()
            filename = extract_filename(file_path)

            # If data looks like an object {}, use it directly
            if data.startswith('{'):
                return f"logger.{level}({message}, {data}, '{filename}')"
            else:
                # Wrap in object
                return f"logger.{level}({message}, {{ data: {data} }}, '{filename}')"

def split_console_args(args: str) -> list:
    """Split console.log arguments respecting braces and quotes"""
    parts = []
    current = ""
    depth = 0
    in_string = False
    string_char = None

    for i, char in enumerate(args):
        if char in ('"', "'", '`') and (i == 0 or args[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None

        if not in_string:
            if char in ('{', '[', '('):
                depth += 1
            elif char in ('}', ']', ')'):
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(current.strip())
                current = ""
                continue

        current += char

    if current.strip():
        parts.append(current.strip())

    return parts

def process_file(file_path: Path) -> tuple[bool, int]:
    """Process a single file, return (modified, count)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if no console.log
        if 'console.log' not in content:
            return False, 0

        original_content = content

        # Add logger import if needed
        if not has_logger_import(content):
            content = add_logger_import(content, file_path)

        # Replace all console.log statements
        pattern = r'console\.log\((.*?)\);?'
        count = 0

        def replacer(match):
            nonlocal count
            count += 1
            return replace_console_log(match, file_path)

        # Multi-line aware replacement
        content = re.sub(pattern, replacer, content, flags=re.DOTALL)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, count

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0

def main():
    """Main execution"""
    # Find all TypeScript files excluding tests
    files = []
    for pattern in ['**/*.ts', '**/*.tsx']:
        for f in FRONTEND_SRC.rglob(pattern):
            # Skip test files, mocks, and logger itself
            if ('test' in str(f).lower() or
                'mock' in str(f).lower() or
                'logger.ts' in f.name or
                'logger.config.ts' in f.name):
                continue
            files.append(f)

    print(f"Found {len(files)} files to process")

    modified = 0
    total_replaced = 0

    for file_path in files:
        was_modified, count = process_file(file_path)
        if was_modified:
            modified += 1
            total_replaced += count
            print(f"✓ {file_path.relative_to(FRONTEND_SRC)}: {count} replacements")

    print(f"\n Summary:")
    print(f"  Files modified: {modified}")
    print(f"  Total console.log replaced: {total_replaced}")

if __name__ == '__main__':
    main()
