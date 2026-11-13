# WDBC：特征减量与良恶性分类比较

在同一数据划分、同一逻辑回归设置下，比较 30、10、5 个细胞核特征的分类表现；以类别比例基线和随机森林作为参照。数据来自课程提供的 WDBC 公开数据，恶性 M=1、良性 B=0。项目不用于临床决策，不将减少模型输入解释为减少检查或费用。

[个人主页](https://aapan818-web.github.io/wdbc-feature-reduction/) · [公开项目展示](https://aapan818-web.github.io/wdbc-feature-reduction/project/) · [查看公开报告源文件](public_report/main.tex) · [学习说明](LEARNING_GUIDE.md)

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

项目页已发布并验证无登录访问。个人主页使用作者提供的四张单人照片，配有原创介绍和课程项目入口；网页照片为压缩副本，原图保留在课程目录。课程提交版报告含学号，保存在本地；公开报告经作者确认只署名“潘冠宇”，不含学号和学院。

## 项目入口

- 分析：`run_analysis.py`；固定配置：`config.json`。
- 真实汇总：`outputs/summary.json`；详细统计与模型指标：`outputs/tables/`。
- 结果图：`outputs/figures/`，同时保存 PNG 和 PDF。
- 交互项目页：`docs/project/index.html`，可直接用浏览器打开。
- 教学顺序：`LEARNING_GUIDE.md`；教学 Notebook：`notebooks/analysis.ipynb`。
- 报告生成：`scripts/build_report.py`；本地提交版在 `report/`，公版在 `public_report/`。
- 数据与软件来源：`DATA_AND_SOFTWARE.md`。
- 公开报告与打包核对：`public_report/qa.json`、`public_report/package_manifest.json`。

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
python scripts/build_report.py --public
```

本地报告生成器读取实际 `outputs/summary.json`、测试预测 CSV 和 `profile.private.json`；公版只读取公开配置，不读取私有署名文件。缺少署名或公开链接会明确列为待补，不会编造。随后使用 XeLaTeX/BibTeX 流程，或 Tectonic 分别编译 `report/main.tex` 与 `public_report/main.tex`。两版本地编译均已核验；课程提交版也已在 Overleaf 显式选择 XeLaTeX 后生成 PDF，最终界面显示 0 错误、0 警告。在线字体与本机不同，页数可能不同，需以内容和实际数值核对。

编译完成后打包源码，再更新网页中的下载文件：

```bash
python -m pip install -r requirements-report.txt
python scripts/package_reports.py
python scripts/build_site.py
```

只处理公开报告时，打包命令可使用 `python scripts/package_reports.py --public-only`。打包器采用文件白名单，包含主文件、结果宏、表格、参考文献和图，不包含本地身份配置或编译日志。

网页生成器只读取公开配置 `profile.json` 和实际分析输出。`docs/index.html` 为个人主页，`docs/project/index.html` 为课程项目页，两页互相链接。仅在公版授权开关启用时，生成器才复制 `public_report/main.pdf` 和公版源码 ZIP；不会自动发布本地含学号的 `report/main.pdf`。系统 Arial Unicode 字体用于本机中文排版，无该字体时使用 Fandol `.otf` 分支；源码包不包含系统字体。

Overleaf 的默认编译器可能是 pdfLaTeX。首行 `% !TEX program = xelatex` 是编辑器提示，不能代替平台设置；请在项目设置的“编译器”中明确选择 **XeLaTeX**，主文件选择 `main.tex`。如果第 6 行 `\IfFontExistsTF` 报未定义，先检查这一设置。平台的编译时限提示与语法错误是不同问题；是否完整编译还需结合日志、引用和实际 PDF 检查。

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
