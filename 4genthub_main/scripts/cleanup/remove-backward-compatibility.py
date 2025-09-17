#!/usr/bin/env python3
"""
Remove Backward Compatibility Code from 4genthub Project
This script removes all Supabase references and backward compatibility code
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

class BackwardCompatibilityRemover:
    """Remove backward compatibility code from the project"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.removed_imports = set()
        self.cleaned_files = []
        self.errors = []
        
    def clean_imports(self, content: str) -> str:
        """Remove Supabase and deprecated imports"""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip Supabase imports
            if re.search(r'from.*supabase|import.*supabase', line, re.IGNORECASE):
                self.removed_imports.add(line.strip())
                continue
            
            # Skip deprecated imports
            if re.search(r'from.*deprecated|import.*deprecated', line, re.IGNORECASE):
                self.removed_imports.add(line.strip())
                continue
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_backward_compat_code(self, content: str) -> str:
        """Remove backward compatibility code blocks"""
        
        # Remove Supabase configuration blocks
        content = re.sub(
            r'#.*Supabase.*\n(?:.*\n)*?(?=\n#|\n\n|\Z)',
            '',
            content,
            flags=re.MULTILINE | re.IGNORECASE
        )
        
        # Remove backward compatibility blocks
        content = re.sub(
            r'#.*[Bb]ackward.*[Cc]ompat.*\n(?:.*\n)*?(?=\n#|\n\n|\Z)',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # Remove legacy code blocks
        content = re.sub(
            r'#.*[Ll]egacy.*\n(?:.*\n)*?(?=\n#|\n\n|\Z)',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # Remove deprecated functions/classes
        content = re.sub(
            r'@deprecated.*\n.*def.*\n(?:.*\n)*?(?=\ndef|\nclass|\Z)',
            '',
            content,
            flags=re.MULTILINE
        )
        
        # Remove fallback user references
        content = re.sub(
            r'.*fallback.*user.*\n',
            '',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )
        
        # Remove default user context references
        content = re.sub(
            r'.*default.*user.*context.*\n',
            '',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )
        
        # Remove allow_default_user patterns
        content = re.sub(
            r'.*allow.*default.*user.*\n',
            '',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )
        
        return content
    
    def clean_environment_variables(self, content: str) -> str:
        """Remove Supabase and deprecated environment variables"""
        lines = content.split('\n')
        cleaned_lines = []
        
        skip_patterns = [
            r'SUPABASE',
            r'ANON_KEY',
            r'SERVICE_KEY',
            r'JWT_SECRET',  # Old JWT config
            r'LEGACY',
            r'DEPRECATED',
            r'BACKWARD_COMPAT',
            r'DEFAULT_USER',
            r'FALLBACK_USER'
        ]
        
        for line in lines:
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break
            
            if not should_skip:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_file(self, file_path: Path) -> bool:
        """Clean a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            
            # Apply cleaning based on file type
            if file_path.suffix == '.py':
                content = self.clean_imports(content)
                content = self.clean_backward_compat_code(content)
            elif file_path.suffix == '.env' or file_path.name.startswith('.env'):
                content = self.clean_environment_variables(content)
            
            # Clean up multiple empty lines
            content = re.sub(r'\n\n\n+', '\n\n', content)
            
            # Remove trailing whitespace
            content = '\n'.join(line.rstrip() for line in content.split('\n'))
            
            if content != original_content:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                self.cleaned_files.append(str(file_path))
                return True
                
        except Exception as e:
            self.errors.append(f"Error processing {file_path}: {e}")
            
        return False
    
    def clean_directory(self, directory: Path, skip_dirs: Set[str] = None):
        """Clean all files in a directory"""
        if skip_dirs is None:
            skip_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv'}
        
        for file_path in directory.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip specified directories
            if any(skip_dir in str(file_path) for skip_dir in skip_dirs):
                continue
            
            # Process Python and env files
            if file_path.suffix in ['.py', '.env'] or file_path.name.startswith('.env'):
                self.clean_file(file_path)
    
    def generate_report(self) -> str:
        """Generate a cleanup report"""
        report = []
        report.append("=" * 80)
        report.append("BACKWARD COMPATIBILITY CLEANUP REPORT")
        report.append("=" * 80)
        
        if self.dry_run:
            report.append("\n⚠️  DRY RUN MODE - No files were modified\n")
        
        if self.cleaned_files:
            report.append(f"\n✅ Cleaned {len(self.cleaned_files)} files:")
            for file_path in self.cleaned_files[:20]:
                report.append(f"  - {file_path}")
            if len(self.cleaned_files) > 20:
                report.append(f"  ... and {len(self.cleaned_files) - 20} more")
        else:
            report.append("\n✅ No files needed cleaning")
        
        if self.removed_imports:
            report.append(f"\n🗑️  Removed {len(self.removed_imports)} deprecated imports:")
            for import_line in list(self.removed_imports)[:10]:
                report.append(f"  - {import_line}")
            if len(self.removed_imports) > 10:
                report.append(f"  ... and {len(self.removed_imports) - 10} more")
        
        if self.errors:
            report.append(f"\n❌ Encountered {len(self.errors)} errors:")
            for error in self.errors[:5]:
                report.append(f"  - {error}")
        
        report.append("\n" + "=" * 80)
        return '\n'.join(report)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove backward compatibility code')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be cleaned without modifying files')
    parser.add_argument('--path', default='4genthub_main/src',
                       help='Path to clean (default: 4genthub_main/src)')
    args = parser.parse_args()
    
    # Create remover instance
    remover = BackwardCompatibilityRemover(dry_run=args.dry_run)
    
    # Clean the specified directory
    path = Path(args.path)
    if not path.exists():
        print(f"❌ Path does not exist: {path}")
        sys.exit(1)
    
    print(f"🔍 Scanning {path}...")
    remover.clean_directory(path)
    
    # Generate and print report
    report = remover.generate_report()
    print(report)
    
    # Also clean specific files in project root
    root_files = [
        '.env',
        '.env.local',
        '.env.development',
        '.env.production',
        'docker-compose.yml',
        'docker-compose.production.yml'
    ]
    
    for file_name in root_files:
        file_path = Path(file_name)
        if file_path.exists():
            if remover.clean_file(file_path):
                print(f"✅ Cleaned root file: {file_name}")
    
    if not args.dry_run and remover.cleaned_files:
        print(f"\n🎉 Successfully cleaned {len(remover.cleaned_files)} files!")
        print("💡 Remember to:")
        print("  1. Review the changes with: git diff")
        print("  2. Test the application")
        print("  3. Commit the changes")


if __name__ == "__main__":
    main()