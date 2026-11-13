#!/usr/bin/env python3
"""Generate the Chinese LaTeX report strictly from the saved analysis outputs.

This script formats existing results; it never trains models or replaces missing
results with illustrative numbers. Compile report/main.tex with XeLaTeX twice.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
MODEL_KEYS = ["DUMMY", "LR30", "LR10", "LR5", "RF30"]
FEATURE_ZH = {
    "mean_radius": "平均半径", "mean_texture": "平均纹理",
    "mean_smoothness": "平均平滑度", "mean_perimeter": "平均周长",
    "mean_area": "平均面积", "mean_compactness": "平均紧致度",
    "mean_concavity": "平均凹度", "mean_concave_points": "平均凹点数",
    "mean_symmetry": "平均对称性", "mean_fractal_dimension": "平均分形维数",
}


def tex(value: object) -> str:
    mapping = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
               "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
               "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(mapping.get(c, c) for c in str(value))


def number(value, places=3) -> str:
    if value is None:
        return "未定义"
    v = float(value)
    return f"{v:.{places}f}" if math.isfinite(v) else "未定义"


def pvalue(value) -> str:
    if value is None:
        return "未计算"
    v = float(value)
    if v < 0.001:
        return "$<0.001$"
    return f"{v:.3f}"


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def compare_test_errors(path: Path, models: dict, test: dict) -> dict:
    """Describe paired errors from saved predictions, checking summary agreement."""
    rows = read_csv(path)
    if len(rows) != test["n"]:
        raise ValueError("Prediction row count differs from the reported test size")
    labels = [int(row["true_label"]) for row in rows]
    if set(labels) != {0, 1}:
        raise ValueError("Test labels must contain benign=0 and malignant=1")
    if labels.count(0) != test["benign"] or labels.count(1) != test["malignant"]:
        raise ValueError("Prediction label counts differ from the summary")
    predictions, errors = {}, {}
    for key in ("LR30", "LR5"):
        predictions[key] = [int(row[f"{key}_prediction"]) for row in rows]
        if not set(predictions[key]).issubset({0, 1}):
            raise ValueError(f"Nonbinary prediction in {key}")
        actual = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
        errors[key] = set()
        for index, (truth, pred) in enumerate(zip(labels, predictions[key])):
            actual[{(0, 0): "tn", (0, 1): "fp", (1, 0): "fn", (1, 1): "tp"}[(truth, pred)]] += 1
            if truth != pred:
                errors[key].add(index)
        if any(actual[k] != models[key]["test"][k] for k in actual):
            raise ValueError(f"Prediction confusion counts differ from summary for {key}")
    disagreements = sum(a != b for a, b in zip(predictions["LR30"], predictions["LR5"]))
    return {
        "models": ["LR30", "LR5"], "test_n": len(rows),
        "errors": {key: len(value) for key, value in errors.items()},
        "common_errors": len(errors["LR30"] & errors["LR5"]),
        "disagreements": disagreements,
        "disagreement_percent": 100 * disagreements / len(rows),
        "identical_fp_fn_counts": all(models["LR30"]["test"][k] == models["LR5"]["test"][k] for k in ("fp", "fn")),
        "interpretation": "exploratory description under the planned error analysis; no model reselection",
    }


def write_table(name: str, columns: str, header: list[str], rows: list[list[str]], note=""):
    if any(len(row) != len(header) for row in rows):
        raise ValueError(f"Table {name}: every row must have {len(header)} cells")
    out = [r"\begin{center}", r"\small", r"\setlength{\tabcolsep}{5pt}",
           r"\renewcommand{\arraystretch}{1.25}", r"\begin{tabular}{" + columns + "}",
           r"\toprule", " & ".join(header) + r" \tabularnewline", r"\midrule"]
    out += [" & ".join(row) + r" \tabularnewline" for row in rows]
    out += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    if note:
        out.append(r"{\footnotesize " + note + "}")
    (REPORT / "tables" / name).write_text("\n".join(out) + "\n", encoding="utf-8")


def interval(lo, hi, places=3):
    return f"[{number(lo, places)}, {number(hi, places)}]"


def url_or_pending(value):
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        return r"\url{" + value.replace("{", "%7B").replace("}", "%7D") + "}"
    return "待发布并核验公开访问地址"


def figure_block(key: str, caption: str, label: str, figures: dict, width="0.94", landscape=False):
    if key not in figures:
        raise KeyError(f"Missing required figure: {key}")
    src = ROOT / "outputs" / figures[key]
    if src.with_suffix(".pdf").exists():
        src = src.with_suffix(".pdf")
    if not src.exists():
        raise FileNotFoundError(src)
    dest = REPORT / "figures" / src.name
    shutil.copy2(src, dest)
    if landscape:
        return (r"\clearpage\begin{landscape}\thispagestyle{plain}" + "\n" +
                r"\begin{figure}[p]\centering" + "\n" +
                r"\includegraphics[width=0.98\linewidth,height=0.88\textwidth,keepaspectratio]{figures/" + src.name + "}\n" +
                r"\caption{" + caption + "}\\label{" + label + "}\n" +
                r"\end{figure}\end{landscape}\clearpage" + "\n")
    return (r"\begin{figure}[htbp]\centering" + "\n" +
            r"\includegraphics[width=" + width + r"\linewidth,height=0.48\textheight,keepaspectratio]{figures/" + src.name + "}\n" +
            r"\caption{" + caption + "}\\label{" + label + "}\n" + r"\end{figure}" + "\n")


def build(summary_file: Path, public: bool = False):
    global REPORT
    REPORT = ROOT / ("public_report" if public else "report")
    s = json.loads(summary_file.read_text(encoding="utf-8"))
    for k in ("source", "split", "statistics", "models", "comparisons", "default_model", "figures"):
        if k not in s:
            raise KeyError(f"Required summary key missing: {k}")
    models = s["models"]
    for k in MODEL_KEYS:
        if k not in models:
            raise KeyError(f"Required model missing: {k}")
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "tables").mkdir(exist_ok=True)
    (REPORT / "figures").mkdir(exist_ok=True)
    profile_path = ROOT / "profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
    private = {}
    if public:
        # Deliberately do not inspect or read the private profile in public mode.
        if profile.get("public_report_approved") is not True:
            raise ValueError("Public report requires explicit approval in profile.json")
        author = profile.get("public_report_author", "").strip()
        if not author:
            raise ValueError("Public report author must be set in profile.json")
        student_id = institution = ""
    else:
        private_path = ROOT / "profile.private.json"
        private = json.loads(private_path.read_text(encoding="utf-8")) if private_path.exists() else {}
        author = private.get("name") or profile.get("name") or profile.get("author") or profile.get("name_zh") or "署名待确认"
        student_id = private.get("student_id", "待确认")
        institution = private.get("institution", "待确认")
    homepage = profile.get("homepage_url", "")
    project_url = profile.get("project_url", "")
    repository = profile.get("repository_url", "")
    blockers = []
    if author == "署名待确认":
        blockers.append("报告作者署名待用户确认")
    if not homepage:
        blockers.append("个人主页资料由作者后续提供，公开URL待填写并核验")
    if not project_url:
        blockers.append("项目页面公开URL待填写并核验")
    methods = s.get("methods", {})
    repeats = methods.get("bootstrap_repeats", 1000)
    d, t = s["split"]["development"], s["split"]["test"]
    predictions_file = ROOT / "outputs" / "predictions" / "test_predictions.csv"
    error_comparison = compare_test_errors(predictions_file, models, t)
    source, quality = s["source"], s.get("quality", {})
    label_counts = source.get("label_counts", {})
    n_b = label_counts.get("B", label_counts.get("benign", label_counts.get("0")))
    n_m = label_counts.get("M", label_counts.get("malignant", label_counts.get("1")))
    if n_b is None or n_m is None:
        n_b, n_m = d["benign"] + t["benign"], d["malignant"] + t["malignant"]

    write_table("sample.tex", "lrrr", ["数据集", "总数", "良性 B", "恶性 M"], [
        ["全部记录", str(source["rows"]), str(n_b), str(n_m)],
        ["开发集", str(d["n"]), str(d["benign"]), str(d["malignant"])],
        ["最终测试集", str(t["n"]), str(t["benign"]), str(t["malignant"])],
    ], "恶性 M 编码为 1，是全部分类指标的正类；良性 B 编码为 0。")
    stats = s["statistics"]["features"]
    rows = []
    for q in stats:
        b, m = q["benign"], q["malignant"]
        rows.append([FEATURE_ZH.get(q["feature"], tex(q["feature"])),
            f'{number(b["median"])} [{number(b["q1"])}, {number(b["q3"])}]',
            f'{number(m["median"])} [{number(m["q1"])}, {number(m["q3"])}]',
            pvalue(q["p_holm"]), number(q["rank_biserial"]),
            interval(q["rank_biserial_ci_low"],q["rank_biserial_ci_high"])])
    write_table("statistics.tex", "lrrrrr", ["特征", r"\shortstack{良性组\\中位数 [Q1,Q3]}", r"\shortstack{恶性组\\中位数 [Q1,Q3]}", "Holm P", "$r_{rb}$", "95\\% 区间"], rows,
        "统计分析限于开发集。正的秩二列相关表示恶性组通常取值较高；区间为组内有放回重采样的百分位区间。")
    rows = []
    for k in MODEL_KEYS:
        m = models[k]; cv=m["cv"]; test=m["test"]
        rows.append([k, str(m.get("k", "-")), f'{number(cv["mean_auc"],4)} $\\pm$ {number(cv["sd_auc"],4)}',
                     number(test["auc"],4), interval(test["auc_ci_low"],test["auc_ci_high"],4)])
    write_table("performance.tex", "lrrrr", ["模型", "特征数", "开发集 CV AUC", "测试 AUC", "测试 AUC 95\\% 区间"],rows,
        "CV 为共用分层五折上的均值与标准差，标准差不是置信区间。DUMMY 不利用特征与标签的关联。")
    rows = []
    for k in MODEL_KEYS:
        q=models[k]["test"]
        rows.append([k, number(q["sensitivity"]),number(q["specificity"]),number(q["precision"]),number(q["f1"]),number(q["accuracy"])])
    write_table("classification.tex", "lrrrrr", ["模型", "灵敏度", "特异度", "精确率", "F1", "准确率"],rows,
        "阈值均为 0.5。无阳性预测时精确率未定义，表中明确标出；F1 依实际评价实现报告。")
    rows = []
    for k in MODEL_KEYS:
        q=models[k]["test"]
        rows.append([k, str(q["tn"]),str(q["fp"]),str(q["fn"]),str(q["tp"])])
    write_table("confusion.tex", "lrrrr", ["模型", "TN：正确良性", "FP：误判恶性", "FN：漏判恶性", "TP：正确恶性"],rows,
        "全部计数来自同一最终测试集。准确率较高不意味着没有漏判。")
    rows = [[tex(q["contrast"]),number(q["estimate"],4),interval(q["ci_low"],q["ci_high"],4)] for q in s["comparisons"]]
    write_table("differences.tex", "lrr", ["测试集 AUC 差值", "点估计", "成对 bootstrap 95\\% 区间"],rows,
        f"{repeats:,} 次按真实类别分层的成对重采样。差值为减量模型减去 LR30；负值表示减量模型的 AUC 较低。")
    featrows=[]
    for k in ["LR10","LR5"]:
        featrows.append([k, ", ".join(r"\texttt{"+tex(f)+"}" for f in models[k]["features"])])
    write_table("features.tex", r"l>{\raggedright\arraybackslash}p{0.79\linewidth}", ["模型", "完整开发集最终拟合时保留的特征"],featrows,
        "名单来自最终拟合，不是先在全数据筛选得到。不同交叉验证折可能产生不同名单。")
    version_rows = [[tex(k),tex(v)] for k,v in s.get("versions",{}).items()]
    if version_rows:
        write_table("versions.tex", "ll", ["软件", "实际版本"],version_rows)

    macros = {
      "AuthorName":tex(author), "StudentID":tex(student_id), "Institution":tex(institution), "TotalN":str(source["rows"]), "BenignN":str(n_b), "MalignantN":str(n_m),
      "DevelopmentN":str(d["n"]),"TestN":str(t["n"]),"DevelopmentB":str(d["benign"]),"DevelopmentM":str(d["malignant"]),
      "TestB":str(t["benign"]),"TestM":str(t["malignant"]),"BootstrapN":str(repeats),
      "DefaultModel":tex(s["default_model"]),"HomepageURL":url_or_pending(homepage) if homepage else "待补：个人主页资料由作者后续提供", "ProjectURL":url_or_pending(project_url),
      "RepositoryURL":url_or_pending(repository),
    }
    for k in ["LR30","LR10","LR5","RF30"]:
        # TeX control words cannot contain digits; map to unambiguous letter-only names.
        key={"LR30":"LRFull","LR10":"LRTen","LR5":"LRFive","RF30":"RFFull"}[k]
        q=models[k]["test"]
        macros[key+"AUC"]=number(q["auc"],4)
        macros[key+"CVAUC"]=number(models[k]["cv"]["mean_auc"],4)
        macros[key+"FN"]=str(q["fn"])
        macros[key+"FP"]=str(q["fp"])
        macros[key+"Sensitivity"]=number(q["sensitivity"])
    identity_note = "approved public author name only" if public else "contains private course identity; do not publish"
    (REPORT/"results_macros.tex").write_text("% Generated from saved analysis and the applicable profile; " + identity_note + ".\n"+"\n".join("\\newcommand{\\"+k+"}{"+v+"}" for k,v in macros.items())+"\n",encoding="utf-8")

    status_text = "本报告已由真实分析结果生成；作者仍需逐项理解并核对数据、方法、数字、图表和引用。"
    if blockers:
        status_text += "当前提交前待办："+"；".join(blockers)+"。"
    else:
        status_text += "公开地址已填入，但是否已通过未登录访问核验，以项目验收记录为准。"

    # These are direct descriptions of the output; no clinical equivalence conclusion is inferred.
    diff_sentences=[]
    for q in s["comparisons"]:
        lo,hi=float(q["ci_low"]),float(q["ci_high"])
        interpretation = "区间包含 0，无法凭本次结果认定差异方向已稳定确定" if lo<=0<=hi else ("区间位于 0 以下，提示在此次固定模型与测试样本条件下减量模型的 AUC 较低" if hi<0 else "区间位于 0 以上，提示在此次固定模型与测试样本条件下减量模型的 AUC 较高")
        diff_sentences.append(tex(q["contrast"])+" 的差值为 "+number(q["estimate"],4)+"，95\\% 区间为 "+interval(q["ci_low"],q["ci_high"],4)+"；"+interpretation+"。")
    numeric_results="\n".join(diff_sentences)
    error_results = (
        "依据保存的逐条测试预测，LR30 与 LR5 分别误判 "
        + str(error_comparison["errors"]["LR30"]) + "、" + str(error_comparison["errors"]["LR5"])
        + " 条记录，误判样本集合的交集为 " + str(error_comparison["common_errors"]) + " 条。"
        + "在同一批 " + str(error_comparison["test_n"]) + " 条测试记录中，两模型对 "
        + str(error_comparison["disagreements"]) + " 条给出不同类别预测（"
        + number(error_comparison["disagreement_percent"], 1) + r"\%）。"
    )
    if error_comparison["identical_fp_fn_counts"]:
        error_results += "本次两模型的 FN 与 FP 汇总计数相同，但不能据此认为它们错误的样本相同。"
    error_results += "这些数值是既定误判分析下的探索性描述，不保证组合模型能够改善表现，也不据此更改默认模型。"
    quality_rows=[]
    for k,v in quality.items():
        if isinstance(v,(str,int,float,bool)) or v is None:
            quality_rows.append([tex(k),tex(v)])
    if quality_rows:
        write_table("quality.tex", "p{0.57\\linewidth}p{0.3\\linewidth}",["核查项（与输出字段名一致）","结果"],quality_rows)

    figures = s["figures"]
    fb={}
    specifications=[
      ("descriptives_png","开发集三项预设特征的组间分布。图中显示实际观测的离散和重叠，不因其影响分类表现而删除合理极端值。","fig:descriptive"),
      ("correlation_png","开发集 30 个特征的 Spearman 相关结构。颜色表示相关系数；该图为探索性描述，不对所有相关系数进行显著性筛选。","fig:correlation"),
      ("performance_png","预设模型的开发集交叉验证与最终测试表现。两部分使用的数据不同；CV 标准差与测试 bootstrap 区间分别解释。","fig:performance"),
      ("roc_png","最终测试集 ROC 曲线。所有模型在同一批测试样本上评价，使用恶性类别的连续预测分数。","fig:roc"),
      ("selection_png","五折训练中减量模型的特征入选频次，范围为 0--5。该频次只描述本次划分下的选择稳定性，不是真实入选概率。","fig:selection"),
      ("coefficients_png","在完整开发集拟合的逻辑回归模型的标准化系数。系数反映模型内的条件预测关联，受正则化和特征相关性影响。","fig:coefficients"),
      ("bootstrap_png","减量模型相对 LR30 的测试 AUC 差值及成对 bootstrap 不确定性。所有模型在每次重采样中使用相同样本索引。","fig:bootstrap"),
    ]
    for key,caption,label in specifications:
        fb[key]=figure_block(key,caption,label,figures,landscape=(key == "coefficients_png"))

    body = TEX_TEMPLATE
    replacements={
      "@@STATUS@@":tex(status_text),"@@NUMERIC_RESULTS@@":numeric_results,
      "@@AUTHOR_BLOCK@@":r"\author{\AuthorName}" if public else r"\author{\AuthorName\\[0.3em]\small 学号：\StudentID\quad \Institution}",
      "@@REPORT_DIR@@":tex(REPORT.name),
      "@@ERROR_RESULTS@@":error_results,
      "@@STAT_RESULTS@@":"；".join(FEATURE_ZH.get(q["feature"],tex(q["feature"]))+"的秩二列相关为 "+number(q["rank_biserial"])+"（95\\% 区间 "+interval(q["rank_biserial_ci_low"],q["rank_biserial_ci_high"])+"）" for q in stats)+"。",
      "@@QUALITY@@":r"\input{tables/quality.tex}" if quality_rows else "完整质量核查记录见分析输出；本报告不以缺失记录替代实际检查。",
      "@@VERSIONS@@":r"\input{tables/versions.tex}" if version_rows else "软件版本尚未提供，应在提交前补齐。",
      "@@SOURCE_HASH@@":tex(source.get("sha256","尚未记录")),
      "@@STAT_SEED@@":str(methods.get("statistics_bootstrap_seed",20261113)),
      "@@TEST_SEED@@":str(methods.get("test_bootstrap_seed",20261114)),
    }
    replacements.update({"@@"+k.upper()+"@@":v for k,v in fb.items()})
    for a,b in replacements.items():body=body.replace(a,b)
    if "@@" in body:
        raise RuntimeError("Unresolved report template marker")
    (REPORT/"main.tex").write_text(body,encoding="utf-8")
    (REPORT/"references.bib").write_text(BIBLIOGRAPHY,encoding="utf-8")
    provenance={
      "document":"main.tex","source_summary":str(summary_file.relative_to(ROOT)),
      "source_summary_sha256":hashlib.sha256(summary_file.read_bytes()).hexdigest(),
      "source_predictions":str(predictions_file.relative_to(ROOT)),
      "source_predictions_sha256":hashlib.sha256(predictions_file.read_bytes()).hexdigest(),
      "raw_source_sha256":source.get("sha256"),
      "evidence":[
       {"id":"E001","type":"local_dataset","locator":"data/raw/wdbc.csv","supports":"record counts, original features and labels","verification":"machine checks in analysis; human review pending"},
       {"id":"E002","type":"generated_results","locator":"outputs/summary.json","supports":"aggregate analysis results and generated tables","verification":"generated from saved results; human review pending"},
       {"id":"E003","type":"prespecified_plan","locator":"../方案A_背景知识与执行方案.html","supports":"feature counts, models, splits, tests and interpretation boundaries"},
       {"id":"E004","type":"external_dataset_documentation","url":"https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic","doi":"10.24432/C5DW2B","supports":"dataset origin and feature meaning","verification":"opened by agent in task; accountable human verification pending"},
       {"id":"E005","type":"software_method_documentation","url":"https://scikit-learn.org/stable/common_pitfalls.html","supports":"training-only fitted preprocessing"},
       {"id":"E006","type":"saved_test_predictions","locator":str(predictions_file.relative_to(ROOT)),"sha256":hashlib.sha256(predictions_file.read_bytes()).hexdigest(),"supports":"paired LR30/LR5 disagreement and error overlap","verification":"row and label counts plus confusion matrices checked against summary; human review pending"},
      ],
      "numeric_bindings":{
       "tables/sample.tex":["source","split"],"tables/statistics.tex":["statistics.features"],
       "tables/performance.tex":["models.*.cv","models.*.test"],"tables/classification.tex":["models.*.test"],
       "tables/confusion.tex":["models.*.test"],"tables/differences.tex":["comparisons"],
       "tables/features.tex":["models.LR10.features","models.LR5.features"],
       "main.tex:exploratory_error_comparison":["outputs/predictions/test_predictions.csv:true_label,LR30_prediction,LR5_prediction"],
       "results_macros.tex":["source","split","models","default_model","profile.json"] + ([] if public else ["profile.private.json"])},
      "derived_error_comparison":error_comparison,
      "visibility":"public" if public else "local_private",
      "contains_private_identity":bool(private),"public_author_name_approved":public,"submission_ready":False,"human_verifier":None,"pending":blockers+["作者人工核对报告与引用、确认署名及最终提交"]
    }
    (REPORT/"provenance.json").write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REPORT/"build_status.json").write_text(json.dumps({"generated":True,"visibility":provenance["visibility"],"author":author,"pending":blockers,"compilation":"not tested by generation script","source_summary_sha256":provenance["source_summary_sha256"]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"report":str(REPORT/"main.tex"),"tables":len(list((REPORT/"tables").glob('*.tex'))),"figures":len(list((REPORT/"figures").iterdir())),"pending":blockers},ensure_ascii=False,indent=2))


TEX_TEMPLATE = r'''% !TEX program = xelatex
% Generated by scripts/build_report.py from real saved analysis outputs.
\documentclass[UTF8,fontset=none,zihao=-4]{ctexart}
% Locally use the system TrueType font whose Chinese rendering was verified.
% On systems without it (including typical Overleaf projects), use Fandol.
\IfFontExistsTF{Arial Unicode MS}{
  \setCJKmainfont[AutoFakeBold=2]{Arial Unicode MS}
  \setCJKsansfont[AutoFakeBold=2]{Arial Unicode MS}
  \setCJKmonofont{Arial Unicode MS}
  \setCJKfamilyfont{hei}[AutoFakeBold=2]{Arial Unicode MS}
  \setCJKfamilyfont{song}[AutoFakeBold=2]{Arial Unicode MS}
}{
  \setCJKmainfont[BoldFont=FandolSong-Bold.otf,ItalicFont=FandolKai-Regular.otf]{FandolSong-Regular.otf}
  \setCJKsansfont[BoldFont=FandolHei-Bold.otf]{FandolHei-Regular.otf}
  \setCJKmonofont{FandolFang-Regular.otf}
  \setCJKfamilyfont{hei}[BoldFont=FandolHei-Bold.otf]{FandolHei-Regular.otf}
  \setCJKfamilyfont{song}[BoldFont=FandolSong-Bold.otf]{FandolSong-Regular.otf}
}
\providecommand{\heiti}{\CJKfamily{hei}}
\providecommand{\songti}{\CJKfamily{song}}
\usepackage[a4paper,left=24mm,right=24mm,top=23mm,bottom=24mm]{geometry}
\usepackage{amsmath,amssymb,booktabs,array,longtable,graphicx,float,placeins,pdflscape}
\usepackage{xurl}
\usepackage{xcolor,hyperref,fancyhdr,enumitem,caption,microtype}
\hypersetup{colorlinks=true,linkcolor=blue!45!black,citecolor=blue!45!black,urlcolor=blue!45!black,breaklinks=true}
\usepackage[numbers,sort&compress]{natbib}
\setlength{\parindent}{2em}
\setlength{\parskip}{3pt}
\linespread{1.25}
\setlist{nosep,leftmargin=2em}
\captionsetup{font=small,labelfont=bf,labelsep=quad}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{\small Python 课程项目：WDBC 特征减量}
\fancyfoot[C]{\small \thepage}
\setlength{\headheight}{16pt}
\renewcommand{\headrulewidth}{0.3pt}
\graphicspath{{figures/}}
\input{results_macros.tex}
\title{\vspace{-1em}\heiti 乳腺肿块良恶性分类中的特征减量\\[0.6em]\large 5、10、30 个细胞核特征下的分类表现与解释}
@@AUTHOR_BLOCK@@
\date{2026 年 11 月 13 日}
\begin{document}
\maketitle
\thispagestyle{empty}
\begin{abstract}
\noindent\textbf{目的：}在固定模型设置和验证流程下，比较 WDBC 数据中使用全部 30 个特征与保留 10 个或 5 个特征的逻辑回归分类表现，分析特征冗余、筛选稳定性与误判。\textbf{方法：}读取课程提供的公开 WDBC 数据，明确恶性为正类；按类别分层划分开发集与测试集，在开发集内采用共用五折交叉验证。标准化及单变量特征筛选均放入训练管道，另设置无信息基线及随机森林参照。对开发集中三项预设变量进行分布比较、Holm 校正和效应量估计；在测试集报告 AUC、分类指标及分层成对 bootstrap 差值区间。\textbf{结果：}共纳入 \TotalN{} 条记录，开发集 \DevelopmentN{} 条、测试集 \TestN{} 条。LR30、LR10、LR5 的测试 AUC 分别为 \LRFullAUC{}、\LRTenAUC{} 和 \LRFiveAUC{}，对应漏判恶性样本 \LRFullFN{}、\LRTenFN{} 和 \LRFiveFN{} 条。\textbf{结论：}本实验给出了同一数据与固定设置下特征减量的实际表现及不确定性。模型简化的判断须同时考虑排序能力、错误计数和选择稳定性；分数接近不构成等效证明，也不能据此宣称减少临床检查或降低费用。
\end{abstract}
\noindent\textbf{关键词：}WDBC；特征选择；逻辑回归；交叉验证；分类评价；可复现分析

\vspace{0.6em}
\noindent\fcolorbox{blue!30!black}{blue!3}{\parbox{0.94\linewidth}{\small @@STATUS@@}}
\newpage

\section{背景与研究问题}
WDBC 是用于乳腺肿块良恶性分类的公开数据集。输入为乳腺肿块细针穿刺数字图像中提取的细胞核数值特征，目标为已有的良性或恶性标签\cite{uci}. 同一基础特征具有 mean、standard error（SE）和 worst 三类摘要，因此多个变量可能携带相关信息。增加输入数量可能提高表达能力，也可能引入冗余；实际影响需要在一致的验证条件下比较。

本项目回答：在使用相同逻辑回归设置时，将输入从 30 个减为 10 个或 5 个，分类表现、入选特征和错误类型如何变化？主要比较为测试 AUC 差值 $\mathrm{AUC}_{5}-\mathrm{AUC}_{30}$ 和 $\mathrm{AUC}_{10}-\mathrm{AUC}_{30}$。无信息基线帮助理解仅利用类别比例的表现，随机森林作为预设非线性参照。模型设置在评价前固定，不通过反复查看测试分数挑选参数。

本研究属于公开既有数据的回顾性方法比较，不采集新患者，也不预测未来发病。减少数值输入并不等于减少检查次数：这些特征来自同类图像，而非 30 项独立临床检查。本作业不提出临床安全性、成本效益或可部署诊断工具的结论。

\section{数据与方法}
\subsection{来源、字段与读取}
数据来自课程提供的 \texttt{wdbc.csv} 及其配套 \texttt{wdbc.names}，原始来源为 UCI\cite{uci}. CSV 无表头，读取时使用 \texttt{header=None}，再赋予固定的 32 个字段名，避免将第一条样本当成列名。ID 用于追踪记录，不作为预测输入；标签映射为 B=0、M=1。

30 个输入由半径、纹理、周长、面积、平滑度、紧致度、凹度、凹点、对称性及分形维数各自的三种摘要构成。数据按 10 个 mean、10 个 SE、10 个 worst 排列；worst 在说明文件中指三个最大值的均值，不能解释为病情分级。本项目沿用源数据数值尺度，不为缺少明示单位的字段补造单位。

\subsection{数据质量与预处理}
分析脚本检查行列数、标签范围、数值类型、缺失值、非有限值、重复 ID 和重复特征行。原始文件保持不变，工作数据和划分清单另行保存；核查结果见附录。数据处理不因某条记录降低预测分数而删除它。模型输入移除 ID 与诊断标签，防止标识或答案进入特征矩阵。

逻辑回归使用训练内标准化：$z=(x-\mu_{\mathrm{train}})/\sigma_{\mathrm{train}}$。验证或测试数据只沿用已拟合的参数。LR10 与 LR5 使用 \texttt{SelectKBest(f\_classif)} 保留指定数量的原始变量。该方法逐变量衡量组间区分程度，不穷举组合，也不保证去除相关变量或得到全局最优特征集。标准化、筛选和分类器组成 \texttt{Pipeline}，每个交叉验证折重新拟合，以免验证信息提前进入处理规则\cite{sklearnpitfalls,selectkbest}。

\subsection{数据划分与模型设置}
按类别分层，以随机种子 42 将 80\% 数据分配至开发集、20\% 分配至测试集。开发集采用五折 \texttt{StratifiedKFold}，打乱且随机种子固定为 42；全部模型共用相同折。数据划分构成如下。
\input{tables/sample.tex}

预设模型为：DUMMY 使用 \texttt{strategy=prior}；LR30、LR10、LR5 使用相同 L2 正则化逻辑回归，$C=1$、\texttt{solver=lbfgs}、\texttt{max\_iter=2000}，仅保留特征数量不同；RF30 使用全部 30 个特征，200 棵树、最大深度 4、叶节点最少 5 个样本、随机种子 42。随机森林不要求进行相同的标准化处理。实际参数与软件版本随输出记录；新版 scikit-learn 用 \texttt{l1\_ratio=0} 表达此处预设的 L2 惩罚。

展示默认模型只在三个逻辑回归候选中，根据开发集平均 CV AUC 确定，精确同分时优先较少特征；本次为 \DefaultModel{}。这不是按测试成绩选出的“最佳模型”。全部预设模型在完整开发集上重拟合，再统一评价同一测试集；分类阈值均固定为 0.5，不称为临床最佳阈值。

\subsection{描述统计与三项预设组间比较}
涉及标签的分布探索、相关结构及组间比较限制在开发集。预先选择 \texttt{mean\_radius}、\texttt{mean\_texture}、\texttt{mean\_smoothness}，分别体现大小、纹理和局部边缘变化；报告两组中位数、第一及第三四分位数。对三项变量实施双侧 Mann--Whitney U 检验，使用 Holm 方法校正三项 P 值。该检验针对两组分布，不能在缺乏额外条件时一概称为中位数检验\cite{mannwhitney}。

恶性组作为 U 统计量第一组，秩二列相关定义为
\begin{equation}
r_{rb}=\frac{2U_M}{n_M n_B}-1.
\end{equation}
正值表示恶性组取值通常较高；在良性与恶性组内分别进行 \BootstrapN{} 次有放回重采样，以百分位法得到 95\% 区间，随机种子为 @@STAT_SEED@@。这些统计检验用于描述数据，不用于生成最终模型特征名单。30 个特征的 Spearman 相关热图用于探索信息冗余，不对所有相关系数逐个进行显著性检验。

补充诊断记录组内 Shapiro--Wilk、以中位数为中心的 Levene 检验和 1.5 倍四分位距筛查，结果保存在 \texttt{outputs/diagnostics.json}；这些数值筛查不用于事后切换检验或删除样本。分析按记录独立处理，唯一 ID 本身不能充分证明原始采样的独立性。

\subsection{评价、不确定性与解释}
主要指标为 ROC-AUC，以恶性类别连续分数计算。另报告灵敏度 $TP/(TP+FN)$、特异度 $TN/(TN+FP)$、精确率 $TP/(TP+FP)$、F1 和准确率，并列出混淆计数。无阳性预测时，精确率没有定义，不用一个看似有效的零掩盖这一情形。CV 的均值与标准差描述五折间的波动，标准差不是 95\% 置信区间。

测试 AUC 及两个主要差值采用 \BootstrapN{} 次按真实类别分层的 bootstrap；在每次重复中，所有模型使用同一组重采样索引，保留比较的配对关系，随机种子为 @@TEST_SEED@@。区间取第 2.5 与 97.5 百分位。它们是\textbf{条件于当前训练结果和测试样本的区间}，不包含重新训练、重新划分与重新筛选的全部变异，也不是外部验证。区间包含零不等于证明两个模型等效。

特征入选频次统计每个训练折是否选中某变量，范围为 0--5；最终名单和系数则来自完整开发集重拟合。标准化系数只解释模型内条件预测关联，不作为因果效应或不经验证的临床风险变化。

\section{结果}
\subsection{样本与特征分布}
全部 \TotalN{} 条记录中，良性 \BenignN{} 条、恶性 \MalignantN{} 条。开发集的三项预设变量分布、Holm 校正 P 值及效应量见表格；图~\ref{fig:descriptive} 展示分布重叠，图~\ref{fig:correlation} 呈现特征间的相关结构。不同指标的差异大小需要结合效应量和原始分布解释，不能仅按 P 值给变量排“临床重要性”顺序。
\input{tables/statistics.tex}
@@STAT_RESULTS@@
@@DESCRIPTIVES_PNG@@
@@CORRELATION_PNG@@
\FloatBarrier

\subsection{开发集比较与最终测试}
下表将开发集 CV 与最终测试结果分开呈现。主比较始终是 LR30、LR10、LR5；RF30 的作用是提供另一模型族的参照，DUMMY 用于显示类别比例基线。
\input{tables/performance.tex}
三个逻辑回归模型的开发集平均 CV AUC 分别为 \LRFullCVAUC{}、\LRTenCVAUC{}、\LRFiveCVAUC{}；最终测试 AUC 分别为 \LRFullAUC{}、\LRTenAUC{}、\LRFiveAUC{}。本次 LR10 的测试 AUC 略高于 LR30，但其开发集 CV 均值较低；两套评价上的排序并不完全一致，不能因此在测试后把展示默认模型改为 LR10 或宣称它普遍优于完整模型。
@@PERFORMANCE_PNG@@
测试集中，LR30、LR10、LR5 的恶性召回率分别为 \LRFullSensitivity{}、\LRTenSensitivity{}、\LRFiveSensitivity{}。相应漏判为 \LRFullFN{}、\LRTenFN{}、\LRFiveFN{} 条，误判恶性为 \LRFullFP{}、\LRTenFP{}、\LRFiveFP{} 条。相近的 AUC 不意味着固定阈值下错误计数完全相同，因而需要同时查看排序评价与分类结果。
\input{tables/classification.tex}
\input{tables/confusion.tex}
@@ROC_PNG@@
\FloatBarrier

\subsection{减量差值与不确定性}
\input{tables/differences.tex}
@@NUMERIC_RESULTS@@
这些差值只涉及同一测试集上的预设比较，不能通过是否跨零推导临床非劣效或安全性。由于测试集规模有限，即使只改变少数恶性样本的排序或判断，也可能改变评价结果。
@@BOOTSTRAP_PNG@@
\FloatBarrier

\subsection{入选特征、系数与错误解释}
\input{tables/features.tex}
图~\ref{fig:selection} 展示开发集各折入选频次，横向附录图~\ref{fig:coefficients} 展示最终逻辑回归系数。相关变量可能替代彼此进入较小特征集；入选频次高表示对当前训练划分较稳定，并不证明它是独立病因。最终系数受标准化、正则化及其他入模变量影响，不能把不同模型中系数变化直接理解为变量真实效应变化。
@@SELECTION_PNG@@
@@ERROR_RESULTS@@

误判记录保存在项目内部预测输出中，可通过样本标识回查。错判分析用于说明模型错误及特征重叠，不为个体作诊断解释；仅凭这份特征表无法确定某次漏判对应的临床病理原因。网页展示汇总错误计数，避免将个案展示包装成实际诊疗建议。
\FloatBarrier

\section{讨论与局限}
本项目在相同划分、模型设置和评价规则下比较三种输入数量，回答的是当前数据集上的模型简化问题。主要结果应综合 AUC 差值、区间、灵敏度、错误计数以及筛选稳定性判断；不能仅选最高的测试分数作为结论。若少量变量模型表现接近，它说明在此验证条件下部分信息可能冗余，并不意味着已找到最优特征组合或证明临床等效。

首先，WDBC 是经典公开数据，分类标签和特征来自特定既有收集过程。当前记录缺少支持跨机构、年代、年龄或族群验证的信息；本作业没有外部验证，也不能完成这些亚组的公平性结论。其次，\TestN{} 条测试记录中的恶性样本为 \TestM{} 条，评价仍有较大样本不确定性；当前 bootstrap 没有覆盖训练过程变异。第三，单变量筛选可能保留相关变量，也可能错过依赖变量组合的信号；固定参数控制了比较范围，但不代表每个模型的最优性能。第四，逻辑回归系数和特征入选是预测关联，不构成病因判断。第五，概率分数未进行独立校准与临床效用验证，阈值 0.5 仅是统一比较规则。

最后，特征来自同类细针穿刺图像，减少列数不等于减少侵入性检查、检查费用或患者负担。后续研究可以在独立来源数据上考察稳定性和校准，并预先规定真正有意义的简化标准；这些工作不属于本次课程结果。

\section{课程实现、可复现性与成果展示}
本项目用 pandas 完成无表头 CSV 的读取、类型和质量核查；用 NumPy 与 SciPy 组织数组计算、分布检验和重采样；用 scikit-learn 的管道完成训练内预处理、筛选、模型拟合及评价；用 Matplotlib/Seaborn 生成图表。类与方法、函数、字典、循环及文件路径管理贯穿分析。统计分析、模型评价与网页展示分别对应课程的不同评分环节。

报告由 \texttt{scripts/build\_report.py} 读取 \texttt{outputs/summary.json}，生成汇总数字、表格和图引用；逐条预测文件 \texttt{outputs/predictions/test\_predictions.csv} 用于计算两模型的错误重合与预测不一致情况。脚本核对该文件的行数、类别计数及混淆计数，并在 \texttt{@@REPORT_DIR@@/provenance.json} 中记录两个结果源的 SHA-256，避免手工抄录造成漂移。原始数据校验值、软件版本、随机种子、参数、划分和预测结果保存在项目中。重建报告本身不会训练模型；应先执行分析入口生成真实输出，再重建和编译。现有结果与新环境是否一致，需要实际复跑核验。

\begin{itemize}
\item 个人主页：\HomepageURL。
\item 项目展示页：\ProjectURL。
\item 代码仓库：\RepositoryURL。
\end{itemize}
网页以同一批分析输出为依据，提供 5/10/30 特征方案切换，联动显示特征名单、测试 AUC、恶性召回率及混淆计数。切换只改变预先计算结果的展示，不重新训练，也不据测试表现临时改选模型。仓库首页与本地 HTML 文件不能自动替代公开可访问的个人主页和项目页面；发布后还需在未登录状态下核验链接与下载。

\section{结论}
本作业完成了 WDBC 数据的规范读取、质量检查、开发集统计分析、训练内特征选择及预设模型的独立测试评价。LR30、LR10、LR5 的测试 AUC 为 \LRFullAUC{}、\LRTenAUC{}、\LRFiveAUC{}；特征减量的价值需结合相应不确定性、错误计数和可解释性共同判断。结论限于本公开数据和当前验证设计，不宣称临床等效、降低检查费用或可以直接用于诊断。

\section*{AI 辅助与软件说明}
本项目使用 Codex 辅助设计实现、整理结果及起草报告，并参考 Scientific Agent Skills 的科学写作与方法核查流程\cite{agentskills}. AI 不是作者；署名者需要理解并核对代码、实际输出、文字、引用及页面内容，确认最终提交。所有结果数字来自实际分析输出，AI 辅助不替代实验执行，也不替代对引用和结论的人工核验。

\bibliographystyle{unsrtnat}
\bibliography{references}
\FloatBarrier
\appendix
@@COEFFICIENTS_PNG@@
\section{质量核查与软件版本}
@@QUALITY@@
@@VERSIONS@@
\noindent 原始 CSV 的 SHA-256：\par
{\footnotesize\ttfamily\seqsplit{@@SOURCE_HASH@@}}

\section{提交前核对}
\begin{enumerate}
\item 核对作者署名、个人主页和项目页面；未发布地址不能标为已完成。
\item 对照输出表检查样本数、标签方向、AUC、错误计数和区间。
\item 确认能够解释 Pipeline、特征选择和测试集用途。
\item 检查 PDF 图表、参考文献和链接；公开页面以未登录访问为准。
\item 明确保存真实代码、参数和重跑说明，由署名者完成最终审阅。
\end{enumerate}
\end{document}
'''.replace(r"\usepackage{xcolor,hyperref,fancyhdr,enumitem,caption,microtype}", r"\usepackage{xcolor,hyperref,fancyhdr,enumitem,caption,microtype,seqsplit}")

BIBLIOGRAPHY = r'''@misc{uci,
  author = {{UCI Machine Learning Repository}},
  title = {Breast Cancer Wisconsin (Diagnostic)},
  year = {1995},
  doi = {10.24432/C5DW2B},
  url = {https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic},
  note = {Dataset documentation, accessed 2026-11-13}
}
@misc{sklearnpitfalls,
  author = {{scikit-learn developers}},
  title = {Common pitfalls and recommended practices},
  year = {2026},
  url = {https://scikit-learn.org/stable/common_pitfalls.html},
  note = {Official documentation, accessed 2026-11-13}
}
@misc{selectkbest,
  author = {{scikit-learn developers}},
  title = {SelectKBest},
  year = {2026},
  url = {https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html},
  note = {Official documentation, accessed 2026-11-13}
}
@misc{mannwhitney,
  author = {{SciPy developers}},
  title = {scipy.stats.mannwhitneyu},
  year = {2026},
  url = {https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html},
  note = {Official documentation, accessed 2026-11-13}
}
@misc{agentskills,
  author = {Kassis, Timothy and Agarwal, Vinayak and He, Yuhuan and Patel, Darshil and Brueckner, Aubrey M.},
  title = {Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents},
  year = {2026},
  doi = {10.48550/arXiv.2609.00065},
  url = {https://arxiv.org/abs/2609.00065},
  note = {arXiv preprint; current record checked 2026-11-13}
}
'''


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary",type=Path,default=ROOT/"outputs"/"summary.json")
    parser.add_argument("--public",action="store_true",help="Build the approved author-name-only version without reading the private profile")
    args=parser.parse_args()
    build(args.summary,public=args.public)
