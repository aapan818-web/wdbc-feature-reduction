# WDBC：特征减量与良恶性分类比较

在同一数据划分、同一逻辑回归设置下，比较 30、10、5 个细胞核特征的分类表现；以类别比例基线和随机森林作为参照。数据来自课程提供的 WDBC 公开数据，恶性 M=1、良性 B=0。项目不用于临床决策，不将减少模型输入解释为减少检查或费用。

## 当前成果与边界

数据分析已实际运行，并从原始数据完整重跑核对。13 张结果 CSV 在两次运行之间逐字节一致，核心 summary 数值一致；原始课程数据未修改。

| 模型 | 开发集5折平均AUC | 测试AUC | 漏判恶性 FN | 误判良性 FP |
|---|---:|---:|---:|---:|
| 类别比例基线 | 0.500000 | 0.500000 | 42 | 0 |
| LR30 | 0.995769 | 0.996032 | 3 | 1 |
| LR10 | 0.985139 | 0.997354 | 4 | 1 |
| LR5 | 0.985036 | 0.995701 | 3 | 1 |
| RF30 | 0.986997 | 0.994048 | 4 | 0 |

开发集 455 条（B=285，M=170），测试集 114 条（B=72，M=42）。阈值固定为 0.5。默认模型 LR30 在查看测试结果前按开发集 CV 确定，不能因为 LR10 测试 AUC 略高就事后改选它。

LR5−LR30 的测试 AUC 差为 −0.000331，成对 bootstrap 95% 区间为 [−0.010251，0.009259]；LR10−LR30 为 0.001323，区间为 [−0.006283，0.010251]。这些区间以当前已训练模型为条件，均跨零，不构成等效或临床非劣效证明。

个人主页按作者要求暂缓，等待照片与介绍；项目页已在本地生成。公开站点和远程仓库以实际发布记录为准，本地 HTML 不代表已经上线。课程提交版报告含学号，默认不进入公开仓库。

## 项目入口

- 分析：`run_analysis.py`；固定配置：`config.json`。
- 真实汇总：`outputs/summary.json`；详细统计与模型指标：`outputs/tables/`。
- 结果图：`outputs/figures/`，同时保存 PNG 和 PDF。
- 交互项目页：`docs/project/index.html`，可直接用浏览器打开。
- 教学顺序：`LEARNING_GUIDE.md`；教学 Notebook：`notebooks/analysis.ipynb`。
- 报告生成：`scripts/build_report.py`；本地报告在 `report/`，不纳入公开 Git。
- 数据与软件来源：`DATA_AND_SOFTWARE.md`。
- 执行状态：`PROGRESS.md`。

## 重现分析

使用 Python 3.12 或经验证兼容的版本。第一次运行前，在本项目目录创建独立环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_analysis.py
python scripts/verify_results.py
```

Windows 的激活命令为 `.venv\Scripts\activate`。`requirements.txt` 是实际分析使用的包版本；LaTeX 编译器与 Notebook 编辑器是另外的工具，不包含在该文件中。

程序从 `data/raw/` 读取数据，重新生成 `outputs/` 中的结果。原始数据保持不变。无须下载个人数据、连接 API 或调用付费模型。重跑使用同一设计用于复现，不用于反复试出更有利的测试分数。

在当前 Codex 本机环境，也可使用已经验证的 scientific-core Python；可移植项目不依赖它的绝对路径。

## 报告与网页

```bash
python scripts/build_report.py
python scripts/build_site.py
```

本地报告生成器读取实际 `outputs/summary.json` 和 `profile.private.json`；缺少署名或公开链接会明确列为待补，不会编造。随后使用 XeLaTeX/BibTeX 流程，或 Tectonic 编译 `report/main.tex`。在 Overleaf 导入完整报告源文件后选择 XeLaTeX。

网页生成器只读取公开配置 `profile.json` 和实际分析输出。作者暂缓个人主页时，不生成 `docs/index.html`。公开版报告必须另行确认；生成器只会寻找 `report/public.pdf`，不会自动发布本地含学号的 `report/main.pdf`。

## 方法要点

1. 无表头 CSV 显式命名，ID 排除出输入，记录缺失、重复与非有限值。
2. 先按类别分层划分开发／测试；开发集内部共用五折划分。
3. 标准化、SelectKBest 和逻辑回归都在每折训练部分拟合。
4. 三项预设特征采用分布描述、双侧 Mann–Whitney U、Holm 校正与秩二列相关；相关热图仅作探索描述。
5. 所有预设模型在完整开发集重拟合后评价同一测试集；固定阈值 0.5。
6. 测试 AUC 差值使用同一批分层重采样病例，保留模型比较的配对结构。
7. 特征入选频次和系数解释模型行为，不作为因果结论。

## 验证证据

- `outputs/run_manifest.json`：真实依赖、来源 SHA、配置 SHA 和运行记录。
- `outputs/frozen_selection.json`：测试评价前保存的开发集选择结果。
- `outputs/verification.json`：分析及图形核查。
- `outputs/independent_verification.json`：独立读取预测和模型，重算 AUC、计数及效应方向。
- `outputs/reproducibility.json`：完整第二次运行的数值一致性核对。

这些证据支持本地结果可追溯和数值可复现，不能证明外部适用性或代替作者理解。

## AI 辅助与个人学习

代码和初稿使用 Codex 辅助制作。作者需要对分析方法、实际结果及最终表述负责，并按课程要求说明辅助情况。Git 提交应如实记录修改；自动生成的提交不应冒充作者本人完成了教程中的两次学习任务。来源与软件引用见 `DATA_AND_SOFTWARE.md`。
