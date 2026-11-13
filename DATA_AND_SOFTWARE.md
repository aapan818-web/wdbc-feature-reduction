# 数据来源与软件说明

## 数据

使用课程文件夹中提供的 Wisconsin Diagnostic Breast Cancer（WDBC）数据副本：`data/raw/wdbc.csv` 与 `data/raw/wdbc.names`。原始课程材料不修改。运行程序会计算 SHA-256 并写入 `outputs/summary.json` 与运行记录，便于确认输入版本。

- 官方记录：[UCI WDBC](https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic)
- 数据集 DOI：[10.24432/C5DW2B](https://doi.org/10.24432/C5DW2B)
- UCI 页面当前许可：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，核对日期 2026-11-13。
- 数据创建者见原始 `wdbc.names`：William H. Wolberg、W. Nick Street、Olvi L. Mangasarian。

本项目添加列名、编码目标标签、划分开发与测试样本并生成分析结果；没有修改原始观测值，也没有增加来自个人体检或合作研究的数据。公开数据许可不应被延伸解释为任何临床使用许可。

## 分析与图表

核心软件为 Python、NumPy、pandas、SciPy、statsmodels、scikit-learn、Matplotlib、Seaborn 和 joblib。实际运行的版本在 `requirements.txt` 与 `outputs/run_manifest.json` 中记录。重现时应使用兼容的 Python 版本，不能仅根据工具文档中的示例版本填写环境。

统计方法定义参考 [SciPy Mann–Whitney U](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html)；特征筛选与数据泄漏参考 [SelectKBest](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html) 及 [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html)。

## AI 辅助与过程核查

代码、报告草稿和项目页面在 Codex 辅助下制作；输出数值来自本项目程序的实际运行。作者仍需理解分析方法，核对结果和文字，并按课程要求说明 AI 辅助情况。自动生成提交记录不等于作者已经亲自完成教程中的学习任务。

统计与图表核查使用了 Scientific Agent Skills 的相关流程，统计诊断辅助代码及来源说明位于 `src/vendor/`。参考：

Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [https://doi.org/10.48550/arXiv.2609.00065](https://doi.org/10.48550/arXiv.2609.00065)。作者与当前记录于 2026-11-13 核对。该引用说明工具来源，不构成对本项目结果的科学认证。

## 本地信息与公开范围

`profile.private.json` 和 `report/` 是本地课程提交材料，其中可能包含学号及署名信息，默认不纳入 Git。个人主页由作者补充照片和介绍后继续。公开仓库与项目页只发布经过范围确认的文件；不得把本地提交报告自动当成公开版上传。
