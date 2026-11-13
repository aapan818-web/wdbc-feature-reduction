#!/usr/bin/env python3
"""从项目根目录一键运行：python run_analysis.py。

本脚本读取原始数据副本，重建 outputs 中的分析结果，不改写课程原始资料。
报告和网页由各自构建脚本读取 outputs/summary.json，避免手抄数值。
"""
from pathlib import Path
from src.analysis import run

if __name__ == '__main__':
    run(Path(__file__).resolve().parent)
