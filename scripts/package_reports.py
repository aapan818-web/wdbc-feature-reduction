#!/usr/bin/env python3
"""Package already generated LaTeX sources using an explicit file allowlist.

Run after compiling the matching PDF. This does not publish anything or certify
human review. Public mode reads only the public profile and public report files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package(public: bool) -> dict:
    folder = ROOT / ("public_report" if public else "report")
    files = [folder / name for name in ("main.tex", "results_macros.tex", "references.bib")]
    files += sorted((folder / "tables").glob("*.tex"))
    files += sorted((folder / "figures").glob("*.pdf"))
    if not (folder / "tables").is_dir() or not (folder / "figures").is_dir():
        raise FileNotFoundError("Generate the report sources before packaging")
    if not all(file.is_file() for file in files):
        raise FileNotFoundError("Required report source is missing")
    pdf = folder / "main.pdf"
    reader = PdfReader(pdf)
    if not reader.pages:
        raise ValueError("Compiled report has no pages")
    if public:
        profile = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        if profile.get("public_report_approved") is not True:
            raise ValueError("Public report has not been approved")
        macros = (folder / "results_macros.tex").read_text(encoding="utf-8")
        for command in (r"\newcommand{\StudentID}{}", r"\newcommand{\Institution}{}"):
            if command not in macros:
                raise ValueError("Public identity macros must be empty")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if profile.get("public_report_author", "").strip() not in text or "学号：" in text:
            raise ValueError("Public PDF identity does not match the approved edition")
    readme = """# 报告源码使用说明

上传此 ZIP 到 Overleaf，选择 XeLaTeX，主文件设为 main.tex。
本地也可运行 tectonic main.tex；或依次运行 xelatex main.tex、
bibtex main、xelatex main.tex、xelatex main.tex。

包内包含结果宏、9 张表、7 幅矢量图和参考文献，数字来自保存的实际结果。
本机已验证 Tectonic 编译；尚未执行 Overleaf 在线编译。
中文字体优先使用系统 Arial Unicode MS，不存在时使用 Fandol .otf 字体。
源码包不分发系统字体。重新分析请使用 GitHub 仓库中的分析程序。

个人主页及作者最终复核仍待完成，不能将本包视为已经正式提交的作业。
"""
    readme += "\n版本：仅含已批准的公开署名。\n" if public else "\n版本：本地课程提交版，含私人身份信息，请勿公开。\n"
    entries = {file.relative_to(folder).as_posix(): file.read_bytes() for file in files}
    entries["README.md"] = readme.encode("utf-8")
    (folder / "README.md").write_text(readme, encoding="utf-8")
    archive = folder / "overleaf_source.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
        for name, data in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            output.writestr(info, data)
    with ZipFile(archive) as check:
        if check.testzip() is not None or set(check.namelist()) != set(entries):
            raise ValueError("Archive validation failed")
        if any(check.read(name) != data for name, data in entries.items()):
            raise ValueError("Archived source differs from the source file")
    manifest = {
        "visibility": "public" if public else "local_private",
        "archive": archive.name, "archive_sha256": digest(archive.read_bytes()),
        "compiled_pdf_sha256": digest(pdf.read_bytes()), "pdf_pages": len(reader.pages),
        "entries": [{"path": name, "sha256": digest(data)} for name, data in sorted(entries.items())],
        "source_only": True, "font_files_bundled": False,
        "online_overleaf_compilation_tested": False,
    }
    (folder / "package_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"folder": folder.name, "entries": len(entries), "pdf_pages": len(reader.pages), "archive_sha256": manifest["archive_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-only", action="store_true")
    args = parser.parse_args()
    if not args.public_only:
        print(json.dumps(package(False), ensure_ascii=False))
    print(json.dumps(package(True), ensure_ascii=False))
