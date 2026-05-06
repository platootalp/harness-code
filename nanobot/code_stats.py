#!/usr/bin/env python3
"""
代码统计工具 - 统计项目中的代码行数和函数数量
支持: Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, Ruby, PHP
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict


# 语言配置: 扩展名 -> (语言名称, 行注释, 块注释开始, 块注释结束)
LANGUAGE_CONFIG = {
    '.py': ('Python', '#', None, None),
    '.js': ('JavaScript', '//', '/*', '*/'),
    '.ts': ('TypeScript', '//', '/*', '*/'),
    '.jsx': ('JSX', '//', '/*', '*/'),
    '.tsx': ('TSX', '//', '/*', '*/'),
    '.java': ('Java', '//', '/*', '*/'),
    '.go': ('Go', '//', '/*', '*/'),
    '.rs': ('Rust', '//', '/*', '*/'),
    '.c': ('C', '//', '/*', '*/'),
    '.h': ('C Header', '//', '/*', '*/'),
    '.cpp': ('C++', '//', '/*', '*/'),
    '.hpp': ('C++ Header', '//', '/*', '*/'),
    '.cs': ('C#', '//', '/*', '*/'),
    '.rb': ('Ruby', '#', '=begin', '=end'),
    '.php': ('PHP', '//', '/*', '*/'),
    '.swift': ('Swift', '//', '/*', '*/'),
    '.kt': ('Kotlin', '//', '/*', '*/'),
    '.scala': ('Scala', '//', '/*', '*/'),
}


# 函数定义正则表达式
FUNCTION_PATTERNS = {
    'Python': r'^\s*def\s+\w+\s*\(',
    'JavaScript': r'^\s*(async\s+)?function\s+\w+|^\s*\w+\s*[=:]\s*(async\s*)?\([^)]*\)\s*=>|^\s*\w+\s*\([^)]*\)\s*\{',
    'TypeScript': r'^\s*(async\s+)?function\s+\w+|^\s*\w+\s*[=:]\s*(async\s*)?\([^)]*\)\s*=>|^\s*\w+\s*\([^)]*\)\s*[:\{]',
    'JSX': r'^\s*(async\s+)?function\s+\w+|^\s*\w+\s*[=:]\s*(async\s*)?\([^)]*\)\s*=>|^\s*\w+\s*\([^)]*\)\s*\{',
    'TSX': r'^\s*(async\s+)?function\s+\w+|^\s*\w+\s*[=:]\s*(async\s*)?\([^)]*\)\s*=>|^\s*\w+\s*\([^)]*\)\s*[:\{]',
    'Java': r'^\s*(public|private|protected|static|\s)+[\w<>\[\]]+\s+\w+\s*\(',
    'Go': r'^\s*func\s+\w+\s*\(',
    'Rust': r'^\s*(async\s+)?(unsafe\s+)?fn\s+\w+',
    'C': r'^\s*[\w\s\*]+\w+\s*\([^)]*\)\s*\{',
    'C Header': r'^\s*[\w\s\*]+\w+\s*\([^)]*\)\s*;',
    'C++': r'^\s*[\w\s\*:<>,]+\w+\s*\([^)]*\)\s*(const\s*)?\{',
    'C++ Header': r'^\s*[\w\s\*:<>,]+\w+\s*\([^)]*\)\s*(const\s*)?[;{]',
    'C#': r'^\s*(public|private|protected|static|internal|\s)+[\w<>\[\]]+\s+\w+\s*\(',
    'Ruby': r'^\s*def\s+\w+',
    'PHP': r'^\s*(public|private|protected|static|\s)*function\s+\w+',
    'Swift': r'^\s*(func\s+\w+|init\s*\(|\s*deinit)',
    'Kotlin': r'^\s*(fun\s+\w+|init\s*\{)',
    'Scala': r'^\s*def\s+\w+',
}


class CodeStats:
    def __init__(self, project_path: str, exclude_dirs: list = None):
        self.project_path = Path(project_path).resolve()
        self.exclude_dirs = set(exclude_dirs or [
            'node_modules', '.git', '__pycache__', 'venv', '.venv',
            'env', '.env', 'dist', 'build', 'target', '.idea',
            '.vscode', 'vendor', 'bin', 'obj', 'out'
        ])
        self.stats = defaultdict(lambda: {
            'files': 0,
            'total_lines': 0,
            'code_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'functions': 0
        })

    def should_process(self, file_path: Path) -> bool:
        """检查是否应该处理该文件"""
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return False
        return file_path.suffix in LANGUAGE_CONFIG

    def analyze_file(self, file_path: Path) -> dict:
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            print(f"警告: 无法读取文件 {file_path}: {e}")
            return None

        lang = LANGUAGE_CONFIG[file_path.suffix][0]
        line_comment = LANGUAGE_CONFIG[file_path.suffix][1]
        block_start = LANGUAGE_CONFIG[file_path.suffix][2]
        block_end = LANGUAGE_CONFIG[file_path.suffix][3]

        total_lines = len(lines)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0
        in_block_comment = False
        functions = 0

        function_pattern = FUNCTION_PATTERNS.get(lang)

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            if block_start and block_end:
                if in_block_comment:
                    comment_lines += 1
                    if block_end in stripped:
                        in_block_comment = False
                    continue
                elif block_start in stripped:
                    comment_lines += 1
                    if block_end not in stripped:
                        in_block_comment = True
                    continue

            if line_comment and stripped.startswith(line_comment):
                comment_lines += 1
                continue

            code_lines += 1

            if function_pattern and re.match(function_pattern, line):
                functions += 1

        return {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines,
            'functions': functions
        }

    def scan_project(self):
        """扫描整个项目"""
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                file_path = Path(root) / file
                if self.should_process(file_path):
                    lang = LANGUAGE_CONFIG[file_path.suffix][0]
                    result = self.analyze_file(file_path)
                    if result:
                        self.stats[lang]['files'] += 1
                        for key, value in result.items():
                            self.stats[lang][key] += value

    def print_report(self):
        """打印统计报告"""
        print("\n" + "=" * 80)
        print(f"代码统计报告: {self.project_path}")
        print("=" * 80)

        if not self.stats:
            print("未找到支持的代码文件")
            return

        header = f"{'语言':<15} {'文件数':>8} {'总行数':>10} {'代码行':>10} {'注释行':>10} {'空行':>8} {'函数数':>8}"
        print(header)
        print("-" * 80)

        totals = {
            'files': 0, 'total_lines': 0, 'code_lines': 0,
            'comment_lines': 0, 'blank_lines': 0, 'functions': 0
        }

        sorted_stats = sorted(
            self.stats.items(),
            key=lambda x: x[1]['code_lines'],
            reverse=True
        )

        for lang, stat in sorted_stats:
            row = f"{lang:<15} {stat['files']:>8} {stat['total_lines']:>10} {stat['code_lines']:>10} " \
                  f"{stat['comment_lines']:>10} {stat['blank_lines']:>8} {stat['functions']:>8}"
            print(row)

            for key in totals:
                totals[key] += stat[key]

        print("-" * 80)
        total_row = f"{'总计':<15} {totals['files']:>8} {totals['total_lines']:>10} {totals['code_lines']:>10} " \
                    f"{totals['comment_lines']:>10} {totals['blank_lines']:>8} {totals['functions']:>8}"
        print(total_row)

        if totals['code_lines'] > 0:
            ratio = totals['comment_lines'] / totals['code_lines'] * 100
            print(f"\n代码注释比: {ratio:.1f}%")

        print("=" * 80)


def main():
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."

    if len(sys.argv) > 2:
        exclude_dirs = sys.argv[2].split(',')
    else:
        exclude_dirs = None

    stats = CodeStats(project_path, exclude_dirs)
    stats.scan_project()
    stats.print_report()


if __name__ == "__main__":
    main()
