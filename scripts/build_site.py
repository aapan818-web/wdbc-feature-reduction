#!/usr/bin/env python3
"""Build the two local/GitHub Pages-compatible pages from verified analysis outputs.

No training or publication occurs here. Run after outputs/summary.json exists.
Optional profile.json fields: display_name, username, bio, github_url,
repository_url, homepage_status. The report must be report/public.pdf.
"""
from pathlib import Path
import csv
import html
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
DOCS = ROOT / 'docs'
PROJECT = DOCS / 'project'
ASSETS = PROJECT / 'assets'
DOWNLOADS = PROJECT / 'downloads'
E = lambda value: html.escape(str(value), quote=True)


def number(value, places=3):
    return '未定义' if value is None else f'{float(value):.{places}f}'


def interval(lo, hi):
    return f'[{number(lo)}, {number(hi)}]'


def positive(value):
    return f'{float(value):+.4f}'


def url(value, fallback='#'):
    text = str(value or '')
    return E(text) if text.startswith(('https://', 'http://')) else fallback


def load_profile():
    path = ROOT / 'profile.json'
    profile = json.loads(path.read_text()) if path.exists() else {}
    profile.setdefault('username', 'aapan818-web')
    profile.setdefault('homepage_status', 'deferred_by_user')
    profile.setdefault('display_name', profile.get('name') or profile['username'])
    profile.setdefault('bio', '这里记录 Python 课程中的学习与实践：从数据读取、统计分析到模型评价，让每一项结论都有可追溯的依据。')
    profile.setdefault('github_url', f'https://github.com/{profile["username"]}')
    return profile


CSS = r'''
:root{--paper:#f6f5ef;--white:#fff;--ink:#17312f;--muted:#5d6e68;--line:#d8dfd7;--teal:#14675b;--light:#e7eee5;--orange:#b66639;--navy:#203f4c;--yellow:#e6d89d;--mono:ui-monospace,SFMono-Regular,Consolas,monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:88px}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}a{color:inherit;text-decoration-thickness:1px;text-underline-offset:5px}a:hover{color:var(--teal)}button,a,input{touch-action:manipulation}button{font:inherit}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #c98735;outline-offset:5px}button{cursor:pointer}.skip{position:fixed;top:-100px;left:16px;background:var(--ink);color:#fff;padding:10px;z-index:99}.skip:focus{top:8px}.wrap{width:min(1180px,calc(100% - 80px));margin:0 auto}.topbar{position:sticky;top:0;z-index:5;background:rgba(246,245,239,.98);border-bottom:1px solid var(--line)}.nav{display:flex;align-items:center;justify-content:space-between;min-height:76px;gap:20px}.brand{display:flex;align-items:center;gap:12px;text-decoration:none;font-size:15px;font-weight:700;letter-spacing:.02em}.brand-mark{display:grid;place-items:center;border:1px solid var(--ink);width:35px;height:35px;font-family:var(--mono);font-size:12px}.nav-links{display:flex;align-items:center;gap:26px;font-size:13px}.nav-links a{text-decoration:none}.nav-links a.active{color:var(--teal);border-bottom:1px solid var(--teal)}.eyebrow{display:flex;align-items:center;gap:10px;color:var(--teal);font:11px/1.6 var(--mono);letter-spacing:.13em;text-transform:uppercase}.eyebrow::before{content:'';width:25px;height:1px;background:currentColor}.hero{padding:80px 0 58px}.home-hero{display:grid;grid-template-columns:1.2fr .8fr;gap:60px;align-items:center;min-height:550px}.hero h1{font-size:clamp(36px,4.4vw,58px);letter-spacing:-.04em;line-height:1.3;margin:22px 0}.hero h1 em{font-style:normal;color:var(--teal)}.hero p.lede{color:var(--muted);max-width:690px;font-size:17px;line-height:1.9}.hero .intro{max-width:600px;color:var(--muted)}.button-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.button{display:inline-flex;align-items:center;justify-content:center;gap:20px;text-decoration:none;padding:11px 20px;border:1px solid var(--ink);font-size:13px;background:transparent;color:var(--ink)}.button.primary{background:var(--ink);color:var(--white)}.button:hover{background:var(--light);color:var(--ink)}.button.primary:hover{background:var(--teal);color:var(--white)}.button.disabled{color:var(--muted);border-color:var(--line);cursor:default}.hero-note{font-size:12px;color:var(--muted);margin-top:18px}.research-cover{background:var(--ink);padding:32px;color:#f1f4ea;min-height:330px;position:relative;overflow:hidden}.cover-top{display:flex;justify-content:space-between;color:#c4d5c4;font:10px var(--mono);letter-spacing:.1em}.cover-circles{display:flex;align-items:center;gap:12px;margin:50px 0 38px}.cover-circle{display:flex;align-items:center;justify-content:center;border:1px solid #9faf9e;border-radius:50%;font:32px var(--mono);width:100px;height:100px}.cover-circle:nth-child(2){width:80px;height:80px;background:#d1dcc5;color:var(--ink)}.cover-circle:nth-child(3){width:64px;height:64px;border-color:#cba36e;color:#e5ca9f}.cover-line{height:1px;flex:1;background:#8da89a}.research-cover h2{font-size:19px;line-height:1.6;font-weight:500;margin:0 0 5px}.research-cover p{font-size:12px;line-height:1.9;color:#c4d5c4;margin:0}.section{padding:58px 0;border-top:1px solid var(--line)}.section-head{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:end;margin-bottom:28px}.section-head h2{font-size:30px;line-height:1.4;letter-spacing:-.02em;margin:10px 0 0}.section-head p{color:var(--muted);font-size:14px;margin:0;max-width:600px}.section-number{font:11px var(--mono);color:var(--teal);letter-spacing:.09em}.project-feature{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--line);background:white}.project-feature .feature-body{padding:38px}.project-feature h3{font-size:25px;line-height:1.5;margin:18px 0 16px}.project-feature p{font-size:14px;color:var(--muted)}.tags{display:flex;flex-wrap:wrap;gap:7px}.tag{display:inline-block;padding:3px 9px;background:var(--light);color:var(--teal);font-size:11px}.feature-data{padding:35px;background:#e9eee5;display:flex;flex-direction:column;justify-content:center}.feature-data h4{font-size:14px;font-weight:500;margin:0 0 16px}.mini-row{display:grid;grid-template-columns:45px 1fr 50px;gap:14px;align-items:center;font:12px var(--mono);margin:16px 0}.mini-track{height:10px;background:#d8e0d5}.mini-fill{height:10px;background:var(--teal)}.mini-foot{font-size:11px;color:var(--muted);margin:16px 0 0;line-height:1.8}.learning-list{display:grid;grid-template-columns:repeat(3,1fr);gap:32px}.learning-item{border-top:2px solid var(--ink);padding-top:16px}.learning-item span{font:11px var(--mono);color:var(--teal)}.learning-item h3{font-size:18px;margin:12px 0 8px}.learning-item p{font-size:14px;color:var(--muted);margin:0}.footbar{border-top:1px solid var(--line);padding:28px 0;margin-top:20px;color:var(--muted);font-size:12px}.footer-flex{display:flex;justify-content:space-between;gap:30px}.footer-flex p{margin:0}.project-hero{padding:54px 0 40px}.project-hero h1{max-width:860px}.metadata{display:flex;flex-wrap:wrap;gap:8px 23px;color:var(--muted);font-size:12px;margin-top:24px}.metadata b{color:var(--ink);font-weight:500}.rule{height:1px;background:var(--line);margin:25px 0}.facts{display:grid;grid-template-columns:repeat(4,1fr);padding:22px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.fact{padding:0 22px;border-left:1px solid var(--line)}.fact:first-child{padding-left:0;border-left:0}.fact strong{display:block;font:32px/1.4 var(--mono);font-weight:500}.fact span{font-size:12px;color:var(--muted)}.lab{background:#fff;border:1px solid var(--line);padding:30px}.lab-top{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:24px}.lab-title{margin:0;font-size:17px}.lab-top p{font-size:12px;color:var(--muted);margin:3px 0 0}.switch{display:inline-flex;border:1px solid var(--ink);padding:4px;gap:4px;flex-shrink:0}.switch button{min-width:66px;border:0;background:transparent;padding:9px 14px;font:14px var(--mono);color:var(--ink)}.switch button[aria-pressed=true]{background:var(--ink);color:white}.lab-status{font-size:12px;color:var(--teal);margin:12px 0}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;padding:24px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.metric .caption{font-size:11px;color:var(--muted)}.metric strong{display:block;font:34px/1.5 var(--mono);color:var(--ink);font-weight:400}.metric small{font-size:11px;color:var(--muted);display:block}.experiment-grid{display:grid;grid-template-columns:1fr 1.1fr;gap:36px;margin-top:28px}.panel-label{font-size:13px;margin:0 0 12px;font-weight:600}.matrix{border-collapse:separate;border-spacing:4px;width:100%;font-size:12px;text-align:center}.matrix td,.matrix th{padding:13px 6px;text-align:center;border:0}.matrix th{font-weight:500;color:var(--muted);background:transparent}.matrix td{background:#edf2eb}.matrix td.error{background:#f5e7d8}.matrix .count{display:block;font:30px/1.4 var(--mono);color:var(--ink)}.matrix .cellname{font-size:11px;color:var(--muted)}.feature-list{display:flex;flex-wrap:wrap;gap:6px;align-content:start}.feature-token{font:11px/1.6 var(--mono);padding:5px 9px;border:1px solid var(--line);background:#f6f8f3;overflow-wrap:anywhere}.small{font-size:12px;color:var(--muted);line-height:1.8}.muted{color:var(--muted)}.table-scroll{overflow-x:auto;max-width:100%;border:1px solid var(--line);background:#fff}.results-table{border-collapse:collapse;width:100%;font-size:12px;min-width:850px}.results-table th,.results-table td{padding:13px 14px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}.results-table thead th{background:#e9eee5;font-weight:600}.results-table tbody th{font-weight:600}.results-table td.num{font-family:var(--mono);font-size:12px}.results-table .cv-cell{background:#f3f6f1}.results-table tbody tr:last-child td,.results-table tbody tr:last-child th{border-bottom:0}.results-table .model-current th{box-shadow:inset 3px 0 var(--teal)}.table-caption{display:flex;gap:20px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin:12px 0}.table-caption span::before{content:'';display:inline-block;width:9px;height:9px;margin-right:6px;background:#e9eee5}.table-caption span:last-child::before{background:#fff;border:1px solid #a6b4a7}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px}.figure{margin:0;background:#fff;border:1px solid var(--line);padding:15px}.figure img{display:block;width:100%;height:auto}.figure figcaption{font-size:12px;color:var(--muted);padding:13px 6px 4px;line-height:1.8}.span2{grid-column:1/-1}.method-grid{display:grid;grid-template-columns:1fr 1fr;gap:40px}.method-list{counter-reset:method;margin:0;padding:0;list-style:none}.method-list li{counter-increment:method;border-top:1px solid var(--line);padding:17px 0 17px 38px;position:relative;font-size:14px}.method-list li:before{content:'0' counter(method);position:absolute;left:0;color:var(--teal);font:11px var(--mono);top:21px}.method-list strong{display:block;margin-bottom:5px}.method-list p{margin:0;color:var(--muted);font-size:13px}.note{padding:20px 24px;background:#eaf0e6;border-left:3px solid var(--teal);font-size:13px;color:var(--ink);margin:20px 0}.note.warm{background:#f3ecdf;border-left-color:var(--orange)}.note p{margin:0}.note p+p{margin-top:10px}.boundaries{display:grid;grid-template-columns:repeat(3,1fr);gap:30px}.boundary{border-top:1px solid var(--ink);padding-top:17px}.boundary h3{font-size:16px;margin:0 0 8px}.boundary p{font-size:13px;color:var(--muted);margin:0}.sources{display:grid;grid-template-columns:1fr 1fr;gap:36px}.sources h3{font-size:16px}.sources p,.sources li{font-size:13px;color:var(--muted)}.sources ul{padding-left:18px}.download-list{display:flex;flex-direction:column;gap:10px}.download-list a{display:flex;justify-content:space-between;gap:20px;padding:12px 0;border-bottom:1px solid var(--line);text-decoration:none;font-size:13px}.download-list small{color:var(--muted);font-family:var(--mono)}.contrast{display:flex;gap:20px;padding:15px 0;border-bottom:1px solid var(--line);justify-content:space-between}.contrast b{font-weight:500;font-size:14px}.contrast span{font:13px var(--mono)}details{margin:18px 0;padding:16px 0;border-top:1px solid var(--line)}summary{cursor:pointer;font-size:13px;font-weight:600}.plain-table{border-collapse:collapse;font-size:12px;width:100%;min-width:540px}.plain-table td,.plain-table th{padding:10px;border-bottom:1px solid var(--line);text-align:left}.plain-table th{background:#eef2eb}.pending{border:1px dashed #aebbb1;padding:20px;color:var(--muted);font-size:13px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:950px){.wrap{width:calc(100% - 48px)}.nav-links{gap:17px}.home-hero{gap:32px}.cover-circles{gap:8px}.cover-circle{width:85px;height:85px}.cover-circle:nth-child(2){width:70px;height:70px}.cover-circle:nth-child(3){width:55px;height:55px}.hero h1{font-size:42px}.experiment-grid{gap:20px}.metric strong{font-size:29px}.lab{padding:22px}.project-feature .feature-body{padding:28px}}
@media(max-width:700px){html{scroll-padding-top:72px}.wrap{width:calc(100% - 36px)}.nav{min-height:66px;align-items:center;gap:12px}.brand{font-size:12px;gap:8px}.brand-mark{width:28px;height:28px;font-size:10px}.nav-links{gap:13px;font-size:12px}.nav-links .desktop-only{display:none}.hero{padding:44px 0 32px}.home-hero{display:block;min-height:0}.home-hero .research-cover{margin-top:32px;min-height:280px}.hero h1{font-size:35px}.hero p.lede{font-size:15px}.hero .intro{font-size:14px}.cover-circles{margin:35px 0 30px;max-width:280px}.section{padding:38px 0}.section-head{grid-template-columns:1fr;gap:14px;margin-bottom:22px}.section-head h2{font-size:25px}.section-head p{font-size:13px}.project-feature{grid-template-columns:1fr}.project-feature .feature-body,.feature-data{padding:25px}.project-feature h3{font-size:22px}.learning-list{grid-template-columns:1fr;gap:22px}.learning-item{padding-top:12px}.learning-item h3{margin:8px 0}.facts{grid-template-columns:repeat(2,1fr);gap:24px 0}.fact:nth-child(3){padding-left:0;border-left:0}.fact strong{font-size:26px;white-space:nowrap}.fact{padding-left:18px}.project-hero h1{font-size:34px}.metadata{font-size:11px;gap:5px 15px}.lab{padding:17px}.lab-top{display:block;margin-bottom:18px}.switch{margin-top:18px;width:100%}.switch button{flex:1}.metric-grid{grid-template-columns:1fr 1fr;gap:18px 12px;padding:18px 0}.metric strong{font-size:30px}.experiment-grid,.grid2,.method-grid,.sources,.boundaries{grid-template-columns:1fr}.experiment-grid{gap:24px}.method-grid{gap:16px}.boundaries{gap:24px}.grid2{gap:18px}.figure{padding:8px}.figure figcaption{font-size:11px}.span2{grid-column:auto}.note{padding:17px;font-size:12px}.footer-flex{display:block}.footer-flex p+p{margin-top:10px}.contrast{display:block}.contrast span{display:block;margin-top:5px}.sources{gap:20px}.button-row{gap:10px}.button{padding:10px 14px;font-size:12px}.table-scroll{margin-left:0;margin-right:0}.feature-token{font-size:10px}.footbar{padding:24px 0}.research-cover{padding:25px}.cover-circle{font-size:26px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{.topbar,.button-row,.switch,.skip{display:none}.wrap{width:100%}.hero,.section{padding:20px 0}.hero h1{font-size:28px}.lab,.figure{break-inside:avoid}.table-scroll{overflow:visible}.results-table{min-width:0;font-size:9px}.results-table th,.results-table td{padding:6px}.grid2,.experiment-grid{grid-template-columns:1fr 1fr}body{background:white;font-size:11px}.footbar{font-size:9px}a{text-decoration:none}}
'''


def shell(title, content, profile, is_project=False):
    up = '../' if is_project else ''
    home = ('../index.html' if is_project else 'index.html') if profile.get('homepage_status') != 'deferred_by_user' else 'index.html'
    project_href = 'index.html' if is_project else 'project/index.html'
    name = E(profile['display_name'])
    home_nav = f'<a href="{home}">主页</a>' if profile.get('homepage_status') != 'deferred_by_user' else ''
    section_nav = '<a href="#experiment">交互</a><a href="#results">结果</a><a href="#methods" class="desktop-only">方法</a><a href="#materials">材料</a>' if is_project else ''
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Python课程项目：WDBC乳腺肿块良恶性分类中的特征减量，比较5、10、30个特征的模型表现与不确定性。"><meta name="color-scheme" content="light"><title>{E(title)}</title><link rel="stylesheet" href="{up}assets/site.css"></head><body><a class="skip" href="#main">跳到主要内容</a><header class="topbar"><div class="wrap nav"><a class="brand" href="{home}" aria-label="{name}，{'项目首页' if profile.get('homepage_status') == 'deferred_by_user' else '个人主页'}"><span class="brand-mark" aria-hidden="true">AA</span><span>{name}</span></a><nav class="nav-links" aria-label="主要导航">{home_nav}<a href="{project_href}" {'class="active"' if is_project else ''}>项目</a>{section_nav}<a class="desktop-only" href="{url(profile.get('github_url'))}" target="_blank" rel="noopener noreferrer">GitHub ↗</a></nav></div></header><main id="main">{content}</main><footer class="footbar"><div class="wrap footer-flex"><p>© 2026 {name} · Python 课程学习与实践</p><p>公开数据 · 可复现分析 · 结论限定于本次实验</p></div></footer>{'<script src="assets/results.js"></script><script src="assets/project.js"></script>' if is_project else ''}</body></html>'''


def copy_figure(path):
    if not path:
        return None
    source = (OUT / path).resolve()
    if not source.is_relative_to(OUT.resolve()) or not source.is_file():
        return None
    dest = ASSETS / source.name
    shutil.copy2(source, dest)
    return 'assets/' + dest.name


def figure(path, caption, alt, wide=False):
    source = copy_figure(path)
    if not source:
        return ''
    with (PROJECT/source).open('rb') as handle:
        header = handle.read(24)
    dimensions = f' width="{int.from_bytes(header[16:20], "big")}" height="{int.from_bytes(header[20:24], "big")}"' if header.startswith(bytes.fromhex('89504e470d0a1a0a')) else ''
    return f'<figure class="figure {"span2" if wide else ""}"><a href="{E(source)}" target="_blank" rel="noopener" aria-label="打开大图：{E(alt)}"><img src="{E(source)}" alt="{E(alt)}" loading="lazy"{dimensions}></a><figcaption>{caption}</figcaption></figure>'


def download_files(profile):
    # Only the explicitly prepared public edition may enter the website.
    candidate = ROOT / 'report/public.pdf'
    report = candidate if candidate.is_file() else None
    if report:
        shutil.copy2(report, DOWNLOADS/'report.pdf')
    shutil.copy2(OUT/'summary.json', DOWNLOADS/'summary.json')
    tables = sorted((OUT/'tables').glob('*.csv')) if (OUT/'tables').exists() else []
    for p in tables:
        shutil.copy2(p, DOWNLOADS/p.name)
    return report, tables


def build_home(s, p, report):
    models = s['models']
    bars = ''.join(f'<div class="mini-row"><span>{k} 特征</span><div class="mini-track"><div class="mini-fill" style="width:{models[f"LR{k}"]["test"]["auc"]*100:.3f}%"></div></div><span>{number(models[f"LR{k}"]["test"]["auc"])}</span></div>' for k in [5, 10, 30])
    content = f'''<div class="wrap"><section class="hero home-hero"><div><div class="eyebrow">Learning journal · Python 2026</div><h1>{E(p['display_name'])}<br><em>数据分析学习与实践</em></h1><p class="intro">{E(p['bio'])}</p><div class="button-row"><a class="button primary" href="project/index.html">查看课程项目 <span aria-hidden="true">↗</span></a><a class="button" href="{url(p.get('github_url'))}" target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a></div><p class="hero-note">Python 编程 · 2026 秋季课程</p></div><div class="research-cover" aria-label="本次研究比较30、10、5个特征的分类表现"><div class="cover-top"><span>RESEARCH NOTE / 01</span><span>WDBC</span></div><div class="cover-circles" aria-hidden="true"><span class="cover-circle">30</span><span class="cover-line"></span><span class="cover-circle">10</span><span class="cover-line"></span><span class="cover-circle">5</span></div><h2>特征更少，表现如何变化？</h2><p>同一数据划分 · 同一模型设置<br>用对照实验观察模型简化的取舍</p></div></section>
    <section class="section" id="projects"><div class="section-head"><div><span class="section-number">01 / SELECTED PROJECT</span><h2>课程项目</h2></div><p>从一个具体问题出发，连接数据整理、统计分析、模型评价与结果呈现。</p></div><article class="project-feature"><div class="feature-body"><div class="tags"><span class="tag">医学公开数据</span><span class="tag">特征选择</span><span class="tag">模型评价</span></div><h3>乳腺肿块良恶性分类中的<br>特征减量</h3><p>在相同的实验条件下，比较保留 5、10、30 个细胞核特征的逻辑回归模型。观察性能、信息冗余、错误类型和筛选稳定性。</p><a class="button" href="project/index.html">进入交互展示 <span aria-hidden="true">→</span></a></div><div class="feature-data"><h4>本次独立测试集 · ROC-AUC</h4>{bars}<p class="mini-foot">恶性为正类；柱长范围为 0–1。<br>点估计需结合置信区间阅读，表现接近不代表等效。</p></div></article></section>
    <section class="section" id="learning"><div class="section-head"><div><span class="section-number">02 / LEARNING PATH</span><h2>把课程知识连成流程</h2></div><p>工具各有分工，分析始终围绕同一个研究问题。</p></div><div class="learning-list"><article class="learning-item"><span>01 / READ & ORGANIZE</span><h3>理解数据</h3><p>用 Python、NumPy 和 pandas 检查字段、标签、缺失情况与样本结构，再进入分析。</p></article><article class="learning-item"><span>02 / COMPARE & EVALUATE</span><h3>建立对照</h3><p>通过统计描述、训练内预处理、交叉验证与独立测试，区分拟合表现和验证证据。</p></article><article class="learning-item"><span>03 / EXPLAIN & COMMUNICATE</span><h3>呈现证据</h3><p>让图表、模型指标与报告来自同一批真实输出，记录不确定性和分析边界。</p></article></div></section>
    <section class="section"><div class="section-head"><div><span class="section-number">03 / WORKING PRINCIPLES</span><h2>让结果可以被核对</h2></div><p>保留数据来源与固定配置，清楚区分开发验证和最终测试；讨论模型使用了什么信息，也说明实验没有回答什么问题。</p></div><div class="button-row"><a class="button" href="project/index.html#methods">阅读实验方法 →</a><a class="button" href="project/index.html#materials">查看报告与材料 →</a></div></section></div>'''
    (DOCS/'index.html').write_text(shell(f'{p["display_name"]}｜数据分析学习与实践', content, p))


def model_row(id_, m):
    t, c = m['test'], m['cv']
    return f'<tr data-model-row="{E(id_)}"><th scope="row">{E(id_)}</th><td>{m["k"]}</td><td class="num cv-cell">{number(c["mean_auc"])} ± {number(c["sd_auc"])}</td><td class="num">{number(t["auc"])}</td><td class="num">{interval(t.get("auc_ci_low"),t.get("auc_ci_high"))}</td><td class="num">{number(t["sensitivity"])}</td><td class="num">{number(t["specificity"])}</td><td class="num">{number(t.get("precision"))}</td><td class="num">{number(t["f1"])}</td><td class="num">{number(t["accuracy"])}</td><td class="num">{t["fn"]} / {t["fp"]}</td></tr>'



def compare_errors(summary):
    """Aggregate paired test errors without publishing sample identifiers."""
    with (OUT/'predictions/test_predictions.csv').open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != summary['split']['test']['n']:
        raise ValueError('预测明细与汇总中的测试集样本数不一致')
    keys = [row['row_index'] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('测试预测明细中存在重复行标识')
    errors = {'LR30': set(), 'LR5': set()}
    counts = {name: dict(tn=0, fp=0, fn=0, tp=0) for name in errors}
    disagreement = 0
    for row in rows:
        truth = int(row['true_label'])
        predictions = {name: int(row[name+'_prediction']) for name in errors}
        if truth not in (0, 1) or any(value not in (0, 1) for value in predictions.values()):
            raise ValueError('预测明细应仅含 0/1 标签')
        disagreement += predictions['LR30'] != predictions['LR5']
        for name, prediction in predictions.items():
            counts[name][{(0, 0): 'tn', (0, 1): 'fp', (1, 0): 'fn', (1, 1): 'tp'}[(truth, prediction)]] += 1
            if prediction != truth:
                errors[name].add(row['row_index'])
    for name, values in counts.items():
        if any(value != summary['models'][name]['test'][metric] for metric, value in values.items()):
            raise ValueError(f'{name} 预测明细与模型汇总的混淆矩阵不一致')
    overlap = len(errors['LR30'] & errors['LR5'])
    return {'n': len(rows), 'disagreement': disagreement, 'both_wrong': overlap,
            'both_correct': len(rows) - len(errors['LR30'] | errors['LR5']),
            'lr30_only_wrong': len(errors['LR30'] - errors['LR5']),
            'lr5_only_wrong': len(errors['LR5'] - errors['LR30']), 'counts': counts}


def build_project(s, p, report, tables):
    models = s['models'];methods = s.get('methods', {})
    default = s.get('default_model', 'LR30')
    selected = default if default in ('LR5','LR10','LR30') else 'LR30'
    m = models[selected];t=m['test'];c=m['cv']
    source=s['source'];split=s['split'];dev=split['development'];test=split['test']
    report_button = '<a class="button primary" href="downloads/report.pdf" download>下载完整报告 <span aria-hidden="true">↓</span></a>' if report else '<span class="button disabled">报告待确认公开范围</span>'
    repo = p.get('repository_url')
    code_button = f'<a class="button" href="{url(repo)}" target="_blank" rel="noopener noreferrer">项目代码 <span aria-hidden="true">↗</span></a>' if repo else f'<a class="button" href="{url(p.get("github_url"))}" target="_blank" rel="noopener noreferrer">作者 GitHub <span aria-hidden="true">↗</span></a>'
    model_rows=''.join(model_row(id_,models[id_]) for id_ in ['DUMMY','LR30','LR10','LR5','RF30'])
    feature_tokens=''.join(f'<span class="feature-token">{E(f)}</span>' for f in m['features'])
    comparisons=''.join(f'<div class="contrast"><b>{E(x["contrast"])}</b><span>{positive(x["estimate"])}　95% CI {interval(x["ci_low"],x["ci_high"])}</span></div>' for x in s.get('comparisons',[]))
    figs=s.get('figures',{})
    performance_figs=figure(figs.get('performance_png'),'开发集交叉验证与独立测试分开呈现。CV 标准差描述折间波动，不是置信区间。','五个预设模型的开发集交叉验证与测试AUC比较')+figure(figs.get('roc_png'),'测试集 ROC 曲线；输入为恶性连续预测分数，曲线比较使用相同的测试样本。','五个模型在同一测试集上的ROC曲线')
    statistics_figs=figure(figs.get('descriptives_png'),'开发集中的三项预设变量：细胞核平均半径、纹理和平滑度。观察两类分布及其重叠。','开发集三项预设特征在良性与恶性组中的分布')+figure(figs.get('correlation_png'),'开发集 30 个特征的 Spearman 相关结构。相关图用于描述信息冗余，不直接用于更改预设特征选择规则。','开发集30个特征的Spearman相关热图')
    explanation_figs=figure(figs.get('selection_png'),'入选频次来自开发集五折训练。0–5 次是探索性稳定性描述，不等于真实入选概率。','5和10特征方案在五折训练中的特征入选频次')+figure(figs.get('coefficients_png'),'最终逻辑回归的标准化系数反映模型内的条件预测关联；系数方向与大小不代表病因或临床效应。','逻辑回归模型最终选择特征的标准化系数')
    boot_figure=figure(figs.get('bootstrap_png'),'按真实类别分层，对所有模型使用同一组重采样索引。区间反映固定模型的测试样本抽样不确定性。','减量模型相对30特征模型的测试AUC差及成对bootstrap区间')
    folds=''.join(f'<tr><th scope="row">{E(id_)}</th>'+''.join(f'<td>{number(v)}</td>' for v in models[id_]['cv']['fold_auc'])+'</tr>' for id_ in ['DUMMY','LR30','LR10','LR5','RF30'])
    files='<a href="downloads/report.pdf" download><span>完整研究报告</span><small>PDF ↓</small></a>' if report else '<p class="small">完整报告用于课程提交；公开下载范围尚待作者确认。</p>'
    files+='<a href="downloads/summary.json" download><span>全部模型汇总结果</span><small>JSON ↓</small></a>'
    labels={'test_metrics.csv':'测试集模型指标','cv_metrics.csv':'开发集各折指标','model_test_metrics.csv':'测试集模型指标','model_cv_summary.csv':'开发集模型汇总','cv_fold_metrics.csv':'开发集各折指标','auc_comparisons.csv':'成对 AUC 差比较','descriptive_statistics.csv':'预设变量统计分析','group_comparisons.csv':'预设变量组间比较','feature_selection_frequency.csv':'特征入选频次','bootstrap_comparisons.csv':'成对 bootstrap 比较'}
    for f in tables:
        if f.name in labels:files+=f'<a href="downloads/{E(f.name)}" download><span>{labels[f.name]}</span><small>CSV ↓</small></a>'
    if repo:files+=f'<a href="{url(repo)}" target="_blank" rel="noopener noreferrer"><span>代码、配置与复现说明</span><small>GitHub ↗</small></a>'
    statistics_table=''
    stats=s.get('statistics',{}).get('features',[]) if isinstance(s.get('statistics'),dict) else []
    if stats:
        def pv(v):return '<0.0001' if float(v)<0.0001 else number(v,4)
        statistics_table='<div class="table-scroll" tabindex="0" aria-label="三项预设变量统计分析"><table class="plain-table"><thead><tr><th>预设变量</th><th>良性 · 中位数 [Q1, Q3]</th><th>恶性 · 中位数 [Q1, Q3]</th><th>Holm 校正 P</th><th>秩二列效应量 [95% CI]</th></tr></thead><tbody>'
        for row in stats:
            b,z=row['benign'],row['malignant']
            statistics_table+=f'<tr><th scope="row">{E(row["feature"])}</th><td>{number(b["median"])} [{number(b["q1"])}, {number(b["q3"])}]</td><td>{number(z["median"])} [{number(z["q1"])}, {number(z["q3"])}]</td><td>{E(pv(row["p_holm"]))}</td><td>{number(row["rank_biserial"])} {interval(row["rank_biserial_ci_low"],row["rank_biserial_ci_high"])}</td></tr>'
        statistics_table+='</tbody></table></div>'
    paired = compare_errors(s)
    n30, n5 = paired['counts']['LR30'], paired['counts']['LR5']
    error_analysis = f'''<div id="error-analysis" class="section-head" style="margin-top:35px"><div><span class="section-number">EXPLORATORY / 探索性错误分析</span><h2>相似的指标，会错在相同的样本上吗？</h2></div><p>进一步比较固定阈值下 LR30 与 LR5 的逐条预测。下面是查看测试结果后的描述性补充，不用于调整模型或默认选择规则。</p></div><div class="grid2"><div><table class="matrix" aria-label="LR30与LR5预测错误重叠表"><thead><tr><th scope="col">LR30 / LR5</th><th scope="col">LR5 正确</th><th scope="col">LR5 错误</th></tr></thead><tbody><tr><th scope="row">LR30 正确</th><td><strong class="count" id="error-both-correct">{paired['both_correct']}</strong><span class="cellname">两者都正确</span></td><td class="error"><strong class="count" id="error-lr5-only">{paired['lr5_only_wrong']}</strong><span class="cellname">仅 LR5 错误</span></td></tr><tr><th scope="row">LR30 错误</th><td class="error"><strong class="count" id="error-lr30-only">{paired['lr30_only_wrong']}</strong><span class="cellname">仅 LR30 错误</span></td><td class="error"><strong class="count" id="error-overlap">{paired['both_wrong']}</strong><span class="cellname">两者都错误</span></td></tr></tbody></table><p class="small">同一批 {paired['n']} 条测试记录；阈值均为 0.5。表内计数描述预测是否正确，区别于上方按真实标签划分的混淆矩阵。</p></div><div class="note warm"><p>LR30 漏判 {n30['fn']} 例、误报 {n30['fp']} 例；LR5 漏判 {n5['fn']} 例、误报 {n5['fp']} 例。两个模型同时预测错误的样本为 <strong>{paired['both_wrong']} 例</strong>。</p><p>两者共有 <strong id="error-disagreement">{paired['disagreement']} / {paired['n']}</strong> 条预测不一致（{paired['disagreement']/paired['n']:.1%}）。总体指标接近，仍可能在具体样本上作出不同判断。</p><p>这仅是本次测试划分上的探索性描述，不能说明错误差异的原因、模型等效或临床互换性，也不据此提出个体诊疗解释。</p></div></div>'''
    content=f'''<div class="wrap"><section class="hero project-hero"><div class="eyebrow">课程研究 / 01 · WDBC 公开数据</div><h1>乳腺肿块良恶性分类：<br><em>特征减量的对照研究</em></h1><p class="lede">比较 5、10、30 个细胞核特征下的乳腺肿块良恶性分类表现。保持数据划分、筛选方法和逻辑回归设置一致，观察模型简化带来的变化。</p><div class="button-row">{report_button}{code_button}<a class="button" href="#experiment">探索结果 <span aria-hidden="true">↓</span></a></div><div class="metadata"><span>作者 <b>{E(p['display_name'])}</b></span><span>课程 <b>Python 编程 · 2026 秋</b></span><span>研究类型 <b>公开数据方法比较</b></span></div><div class="facts"><div class="fact"><strong>{source['rows']}</strong><span>原始样本 · B/M 标签</span></div><div class="fact"><strong>{source['features']}</strong><span>细胞核数值特征</span></div><div class="fact"><strong>{dev['n']} / {test['n']}</strong><span>开发样本 / 测试样本</span></div><div class="fact"><strong>5-fold</strong><span>开发集内交叉验证</span></div></div><p class="hero-note">研究范围：已有细针穿刺图像特征的二分类分析。减少输入变量不等于减少临床检查，也不证明诊断安全性。</p></section>
    <section class="section" id="experiment"><div class="section-head"><div><span class="section-number">01 / INTERACTIVE COMPARISON</span><h2>特征减量，改变了什么？</h2></div><p>切换模型，查看同一独立测试集上的表现、最终特征名单与错误计数。切换只改变展示，不重新训练或挑选测试结果。</p></div><div class="lab"><div class="lab-top"><div><h3 class="lab-title">逻辑回归 · 特征数量对照</h3><p>恶性 M=1 · 分类阈值固定为 0.5 · 测试集 {test['n']} 条</p></div><div class="switch" role="group" aria-label="选择逻辑回归的特征数量">{''.join(f'<button type="button" data-model="LR{k}" aria-pressed="{str(selected==f"LR{k}").lower()}" aria-controls="experiment-results">{k} 特征</button>' for k in [5,10,30])}</div></div><div id="experiment-results"><p class="lab-status" id="model-status" role="status" aria-live="polite">当前展示 {E(selected)}：{m['k']} 个特征。开发集 CV AUC {number(c['mean_auc'])} ± {number(c['sd_auc'])}。</p><div class="metric-grid"><div class="metric"><span class="caption">测试 ROC-AUC</span><strong id="metric-auc">{number(t['auc'])}</strong><small id="metric-auc-ci">95% CI {interval(t.get('auc_ci_low'),t.get('auc_ci_high'))}</small></div><div class="metric"><span class="caption">恶性召回率 / 灵敏度</span><strong id="metric-sensitivity">{number(t['sensitivity'])}</strong><small>TP / (TP + FN)</small></div><div class="metric"><span class="caption">特异度</span><strong id="metric-specificity">{number(t['specificity'])}</strong><small>TN / (TN + FP)</small></div><div class="metric"><span class="caption">漏判 / 误报</span><strong id="metric-errors">{t['fn']} / {t['fp']}</strong><small>FN / FP · 原始计数</small></div></div><div class="experiment-grid"><div><h4 class="panel-label">混淆矩阵 · 行为真实标签，列为预测标签</h4><table class="matrix" aria-label="当前模型的测试集混淆矩阵"><thead><tr><th scope="col">真实 / 预测</th><th scope="col">预测良性</th><th scope="col">预测恶性</th></tr></thead><tbody><tr><th scope="row">真实良性</th><td><strong class="count" id="cm-tn">{t['tn']}</strong><span class="cellname">TN · 正确排除</span></td><td class="error"><strong class="count" id="cm-fp">{t['fp']}</strong><span class="cellname">FP · 误报</span></td></tr><tr><th scope="row">真实恶性</th><td class="error"><strong class="count" id="cm-fn">{t['fn']}</strong><span class="cellname">FN · 漏判</span></td><td><strong class="count" id="cm-tp">{t['tp']}</strong><span class="cellname">TP · 正确识别</span></td></tr></tbody></table><p class="small">测试集包含良性 {test['benign']} 条、恶性 {test['malignant']} 条。四格计数之和始终为 {test['n']}。</p></div><div><h4 class="panel-label">完整开发集重拟合后的最终特征</h4><div class="feature-list" id="feature-list">{feature_tokens}</div><p class="small">mean：均值；se：标准误；worst：三个最大值的均值。worst 并非病情等级。名单不来自测试集筛选。</p></div></div></div><noscript><p class="note">当前浏览器未启用 JavaScript。上方显示预设模型，下面的完整结果表仍包含全部五个模型的数据。</p></noscript></div><p class="small">默认展示规则在测试前确定：在三个逻辑回归方案中，按开发集交叉验证平均 AUC 选择，同分优先较少特征。本次记录的默认模型为 <strong>{E(default)}</strong>；模型切换不改变该规则。</p></section>
    <section class="section" id="results"><div class="section-head"><div><span class="section-number">02 / FULL RESULTS</span><h2>五个模型，统一评价条件</h2></div><p>DUMMY 为只学习类别比例的基线；LR30 是主要参照；LR10、LR5 为减量方案；RF30 为非线性参照。所有模型共用数据划分和验证折。</p></div><div class="table-scroll" tabindex="0" aria-label="可横向滚动的完整模型结果表"><table class="results-table"><thead><tr><th scope="col">模型</th><th scope="col">特征数</th><th scope="col">开发 CV AUC · 均值±SD</th><th scope="col">测试 AUC</th><th scope="col">测试 AUC · 95% CI</th><th scope="col">灵敏度</th><th scope="col">特异度</th><th scope="col">精确率</th><th scope="col">F1</th><th scope="col">准确率</th><th scope="col">FN / FP</th></tr></thead><tbody>{model_rows}</tbody></table></div><div class="table-caption"><span>浅绿色列：开发集交叉验证</span><span>其余指标：固定独立测试集</span></div><p class="small">DUMMY 未产生恶性预测时，精确率分母为 0，标为“未定义”；F1 按预先记录的零除约定计算。CV 的 SD 与测试 AUC 的置信区间含义不同。</p><details><summary>展开查看开发集五折 AUC</summary><div class="table-scroll"><table class="plain-table"><thead><tr><th>模型</th><th>第 1 折</th><th>第 2 折</th><th>第 3 折</th><th>第 4 折</th><th>第 5 折</th></tr></thead><tbody>{folds}</tbody></table></div></details><div class="grid2">{performance_figs}</div><div class="section-head" style="margin-top:35px"><div><h2>点估计之外，还看不确定性</h2></div><p>主比较是减量模型与 LR30 的测试 AUC 差。所有模型在同一组分层 bootstrap 样本中成对比较。</p></div>{comparisons}<div class="note warm"><p><strong>区间跨 0 不等于等效。</strong>本项目没有预设临床非劣效界值。bootstrap 区间仅反映固定模型下测试样本的抽样不确定性，不覆盖重新训练和重新筛选特征的全部变异。</p></div>{boot_figure}{error_analysis}</section>
    <section class="section" id="statistics"><div class="section-head"><div><span class="section-number">03 / DATA & STATISTICS</span><h2>先理解分布，再解释模型</h2></div><p>涉及标签的统计分析在开发集进行。三项预设变量采用双侧 Mann–Whitney U 检验，三项 P 值用 Holm 方法校正，同时报告秩二列相关效应量。</p></div><div class="grid2">{statistics_figs}</div>{statistics_table}<div class="note"><p>效应量方向以恶性组为参照：正值表示恶性组通常取值更高。检验描述两组分布，不直接证明因果；统计检验结果不用于临时挑选模型输入。</p></div></section>
    <section class="section" id="explanation"><div class="section-head"><div><span class="section-number">04 / MODEL INTERPRETATION</span><h2>模型保留了哪些信息？</h2></div><p>区分交叉验证中的入选频次与最终模型的特征名单。高度相关的变量可能互相替代，单次选择不能被解释为唯一重要的生物学特征。</p></div><div class="grid2">{explanation_figs}</div></section>
    <section class="section" id="methods"><div class="section-head"><div><span class="section-number">05 / REPRODUCIBLE DESIGN</span><h2>每一步都在规定的数据内完成</h2></div><p>使用预设参数控制实验规模。模型与特征数量方案在查看最终测试结果之前确定，测试后不因分数重新选择种子或调整参数。</p></div><div class="method-grid"><ol class="method-list"><li><strong>读取与核查</strong><p>无表头 CSV 按固定顺序命名；保留 ID 以便追踪，但排除出模型输入。B=0、M=1 的映射贯穿全项目。</p></li><li><strong>固定分层划分</strong><p>80% 开发、20% 测试，种子 42；开发集内使用打乱后的五折分层验证，所有模型共用折索引。</p></li><li><strong>训练内部预处理</strong><p>StandardScaler、SelectKBest(f_classif) 与逻辑回归置于同一 Pipeline。每一折重新拟合，验证与测试仅沿用已有规则。</p></li></ol><ol class="method-list" style="counter-reset:method 3"><li><strong>统一模型配置</strong><p>逻辑回归 L2、C=1、lbfgs、max_iter=2000；随机森林 200 棵树、max_depth=4、min_samples_leaf=5。DUMMY 使用 prior 策略。</p></li><li><strong>最终测试与成对比较</strong><p>完整开发集重拟合后，在同一测试集评价，阈值固定 0.5。按真实类别分层做 {methods.get('bootstrap_repeats',1000):,} 次成对 bootstrap。</p></li><li><strong>由同一输出生成成果</strong><p>页面指标、图表和下载结果来自真实分析输出。网页按钮只切换预计算结果，报告与代码保留来源和配置。</p></li></ol></div></section>
    <section class="section" id="limits"><div class="section-head"><div><span class="section-number">06 / SCOPE & LIMITATIONS</span><h2>这项实验可以说明什么</h2></div><p>它展示特征数量、信息冗余和分类表现之间的关系，为理解模型简化提供实例。结论限定于本数据与预设验证条件。</p></div><div class="boundaries"><article class="boundary"><h3>模型简化 ≠ 检查减量</h3><p>30 个特征来自同类细针穿刺图像。减少模型输入不代表减少检查次数、降低诊疗成本或证明临床安全。</p></article><article class="boundary"><h3>内部验证 ≠ 外部适用</h3><p>本次只使用一个经典公开数据集与一次保留测试划分。现实人群适用性、校准和跨机构表现需要独立验证。</p></article><article class="boundary"><h3>特征贡献 ≠ 因果关系</h3><p>系数与筛选分数描述模型如何使用信息。年龄、族群和医院等资料不足以支持本项目的公平性或病因结论。</p></article></div></section>
    <section class="section" id="materials"><div class="section-head"><div><span class="section-number">07 / MATERIALS & SOURCES</span><h2>报告、数据来源与复现材料</h2></div><p>查看完整方法与结果，或下载汇总数据，核对网页中的指标。</p></div><div class="sources"><div><h3>下载与代码</h3><div class="download-list">{files}</div></div><div><h3>数据与方法来源</h3><ul><li><a href="https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic" target="_blank" rel="noopener noreferrer">UCI · Breast Cancer Wisconsin (Diagnostic)</a>：569 条记录、30 个特征；来源为细针穿刺图像中的细胞核特征。</li><li><a href="https://scikit-learn.org/stable/common_pitfalls.html" target="_blank" rel="noopener noreferrer">scikit-learn · Common pitfalls</a>：训练内预处理与数据泄漏。</li><li><a href="https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html" target="_blank" rel="noopener noreferrer">scikit-learn · SelectKBest</a>：单变量特征筛选。</li><li><a href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html" target="_blank" rel="noopener noreferrer">SciPy · Mann–Whitney U</a>：组间分布比较。</li></ul><p class="small">课程材料：第 3 讲文件读取、第 5–6 讲数组、表格与统计、第 7 讲机器学习、第 8 讲可视化。网页为课程教学展示，不提供个体诊疗判断。</p></div></div></section></div>'''
    (PROJECT/'index.html').write_text(shell('特征减量｜WDBC 课程项目',content,p,True))
    (ASSETS/'results.js').write_text('window.PROJECT_RESULTS = '+json.dumps(s,ensure_ascii=False,allow_nan=False).replace('</', '<' + chr(92) + '/')+';\n')
    (ASSETS/'project.js').write_text(JS)


JS = r'''
(() => {
  'use strict';
  const result = window.PROJECT_RESULTS;
  if (!result || !result.models) return;
  const fmt = (v, n=3) => v == null ? '未定义' : Number(v).toFixed(n);
  const text = (id, value) => { const el = document.getElementById(id); if(el) el.textContent = value; };
  function show(id) {
    const model = result.models[id];
    if(!model || !['LR5','LR10','LR30'].includes(id)) return;
    const t=model.test, c=model.cv;
    document.querySelectorAll('[data-model]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.model === id)));
    document.querySelectorAll('[data-model-row]').forEach(r => r.classList.toggle('model-current',r.dataset.modelRow===id));
    text('model-status',`当前展示 ${id}：${model.k} 个特征。开发集 CV AUC ${fmt(c.mean_auc)} ± ${fmt(c.sd_auc)}。`);
    text('metric-auc',fmt(t.auc));text('metric-auc-ci',`95% CI [${fmt(t.auc_ci_low)}, ${fmt(t.auc_ci_high)}]`);
    text('metric-sensitivity',fmt(t.sensitivity));text('metric-specificity',fmt(t.specificity));text('metric-errors',`${t.fn} / ${t.fp}`);
    for(const cell of ['tn','fp','fn','tp']) text('cm-'+cell,t[cell]);
    const list=document.getElementById('feature-list');list.replaceChildren();
    for(const f of model.features){const item=document.createElement('span');item.className='feature-token';item.textContent=f;list.appendChild(item);}
  }
  document.querySelectorAll('[data-model]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.model)));
  const initial=document.querySelector('[data-model][aria-pressed="true"]');if(initial)show(initial.dataset.model);
})();
'''


def main():
    if not (OUT/'summary.json').exists():
        raise SystemExit('真实分析结果 outputs/summary.json 尚未生成；未填入任何示例数据。')
    s=json.loads((OUT/'summary.json').read_text())
    for key in ['DUMMY','LR30','LR10','LR5','RF30']:
        if key not in s['models']:
            raise ValueError(f'分析结果缺少预设模型 {key}')
    for d in [DOCS/'assets',ASSETS,DOWNLOADS]:d.mkdir(parents=True,exist_ok=True)
    (DOCS/'assets/site.css').write_text(CSS)
    (DOCS/'.nojekyll').write_text('')
    p=load_profile()
    report,tables=download_files(p)
    if p.get('homepage_status') != 'deferred_by_user':
        build_home(s,p,report)
    build_project(s,p,report,tables)
    status={'analysis_loaded':True,'report_available':bool(report),'repository_link_available':bool(p.get('repository_url')),'display_name':p['display_name'],'homepage_status':p.get('homepage_status'),'outputs':['docs/project/index.html']+(['docs/index.html'] if p.get('homepage_status') != 'deferred_by_user' else []),'tables_copied':len(tables)}
    (DOCS/'build_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
    print(json.dumps(status,ensure_ascii=False))


if __name__=='__main__':main()
