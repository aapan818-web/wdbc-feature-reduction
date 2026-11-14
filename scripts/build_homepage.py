#!/usr/bin/env python3
"""Render the personal site from its public photo catalogue. No analysis runs."""
from pathlib import Path
import html
import json

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'https://aapan818-web.github.io/wdbc-feature-reduction/'
E = lambda value: html.escape(str(value), quote=True)
SECTIONS = [('sports','运动','01'),('research','科研','02'),('me','性格与日常','03'),('places','旅行与风景','04'),('pets','宠物','05')]
LABELS = {'basketball':'篮球','flag':'腰旗橄榄球','training':'训练与其他运动','mountains':'山野','water':'水边','cities':'城市','campus':'校园','me':'生活','cats':'柠檬','animals':'路遇'}


def build_homepage(directory=None):
    directory = directory or ROOT / 'homepage'
    content = json.loads((directory / 'content.json').read_text())
    photos, groups = content['photos'], content['groups']

    def img(ident, prefix='', eager=False, cls=''):
        p = photos[str(ident)]
        return f'<img class="{cls}" src="{prefix}assets/gallery/{p["file"]}" width="{p["width"]}" height="{p["height"]}" alt="{E(p["caption"])}" loading="{"eager" if eager else "lazy"}" decoding="async"{chr(32)+"fetchpriority=high" if eager else ""}>'

    def header(slug):
        pre = '../' if slug else ''
        links = ''.join(f'<a href="{pre}{s}/"{ " aria-current=page" if s == slug else ""}>{name}</a>' for s,name,n in SECTIONS)
        return f'''<a class="skip" href="#main">跳到内容</a><header class="site-header"><div class="wrap nav-row">
<a class="brand" href="{pre or './'}" aria-label="潘冠宇，首页"><span class="brand-symbol">潘<span>·</span></span><span class="brand-name">潘冠宇<small>PAN GUANYU</small></span></a>
<nav class="desktop-nav" aria-label="主导航">{links}<a class="nav-follow" href="#follow">抖音见 ↗</a></nav>
<details class="mobile-menu"><summary>目录 <span>＋</span></summary><nav aria-label="移动端导航"><a href="{pre or './'}">首页</a>{links}<a href="#follow">抖音见 ↗</a></nav></details></div></header>'''

    def follow():
        return '''<section class="follow-section" id="follow"><div class="wrap follow-grid"><div><p class="eyebrow">KEEP IN TOUCH</p><h2>抖音里，<br>叫我<span>潘潘潘冠冠。</span></h2></div><div class="follow-account"><p>篮球、运动，还有生活里好玩的事。</p><label for="douyin-handle">抖音号</label><div class="account-line"><input id="douyin-handle" aria-label="抖音号" value="83008883411" readonly><button type="button" class="copy-button" data-copy="83008883411" hidden>复制号码 ↗</button></div><a class="text-link" href="https://www.douyin.com/" target="_blank" rel="noopener noreferrer">打开抖音，搜索账号 <span>↗</span></a><p class="status" data-copy-status role="status" aria-live="polite"></p></div></div></section>'''

    def footer(slug):
        pre = '../' if slug else ''
        return f'<footer class="wrap footer"><a href="{pre or "./"}">潘冠宇 © 2026</a><span>认真打球，也认真去玩。</span><a href="#top">回到顶部 ↑</a></footer>'

    def next_pages(slug):
        return '<aside class="wrap next-pages"><p class="eyebrow">ANOTHER SIDE</p><h2>再看看我的另一面。</h2><div>'+''.join(f'<a href="../{s}/"><small>{n}</small>{name}<span>↗</span></a>' for s,name,n in SECTIONS if s!=slug)+'</div></aside>'

    def gallery(keys, prefix='../', heading='相册', limit=12):
        ids = [i for key in keys for i in groups[key]]
        filters = ''.join(f'<button type="button" data-filter="{key}" aria-pressed="false">{LABELS[key]} <small>{len(groups[key])}</small></button>' for key in keys)
        figures = ''
        for ident in ids:
            p = photos[ident]
            figures += f'''<figure class="gallery-item" data-group="{p['group']}"><a class="photo-link" href="{prefix}assets/gallery/{p['file']}" data-caption="{E(p['caption'])}" aria-label="放大查看：{E(p['caption'])}" target="_blank" rel="noopener">{img(ident,prefix)}<span class="photo-zoom" aria-hidden="true">↗</span></a><figcaption><span>{E(p['caption'])}</span><small>{LABELS[p['group']]}</small></figcaption></figure>'''
        return f'''<section class="wrap gallery-section" id="gallery" data-gallery data-limit="{limit}"><div class="section-heading"><div><p class="eyebrow">PHOTO JOURNAL</p><h2>{heading}</h2></div><p class="gallery-count" data-gallery-count aria-live="polite">{len(ids)} 张照片</p></div><div class="filter-row" data-filters hidden><button type="button" data-filter="all" aria-pressed="true">全部 <small>{len(ids)}</small></button>{filters}</div><div class="photo-grid">{figures}</div><div class="gallery-bottom"><button type="button" class="button outline" data-more hidden>再看 12 张 ↓</button></div></section>'''

    def page(slug,title,description,body,cover):
        pre = '../' if slug else ''
        canonical = BASE_URL + (slug+'/' if slug else '')
        return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{E(title)}｜潘冠宇</title><meta name="description" content="{E(description)}"><meta name="theme-color" content="#f4f1e9"><meta name="color-scheme" content="light"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:title" content="{E(title)}｜潘冠宇"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE_URL}assets/gallery/{photos[str(cover)]['file']}"><link rel="icon" href="{pre}assets/mark.svg" type="image/svg+xml"><link rel="stylesheet" href="{pre}assets/journal.css"><script src="{pre}assets/journal.js" defer></script></head><body class="page-{slug or 'home'}" id="top">{header(slug)}<main id="main">{body}{next_pages(slug) if slug else ''}{follow()}</main>{footer(slug)}<dialog class="lightbox" aria-label="照片查看器"><div class="lightbox-top"><p data-lightbox-counter></p><button type="button" data-close aria-label="关闭照片">关闭 ×</button></div><div class="lightbox-stage"><button type="button" data-prev aria-label="上一张照片">←</button><img data-lightbox-image alt=""><button type="button" data-next aria-label="下一张照片">→</button></div><div class="lightbox-caption"><p data-lightbox-caption></p><a data-lightbox-original target="_blank" rel="noopener">打开大图 ↗</a></div></dialog></body></html>'''

    def intro(slug,eyebrow,title,description):
        return f'''<div class="wrap breadcrumb"><a href="../">首页</a><span>/</span><span>{dict((s,n) for s,n,i in SECTIONS)[slug]}</span><button class="share-button" type="button" data-share hidden>分享这一页 ↗</button><span class="share-status" role="status" aria-live="polite"></span></div><section class="wrap chapter-intro"><div><p class="eyebrow">{eyebrow}</p><h1>{title}</h1></div><p class="chapter-description">{description}</p></section>'''

    # The home contains only selected covers. All photo sequences live on the detail pages.
    home = f'''<section class="wrap home-hero"><div class="hero-copy"><p class="eyebrow"><span class="red-dot"></span> HI, I'M PAN GUANYU.</p><h1>认真打球，<br>也认真<span class="serif">去玩。</span></h1><p class="hero-bio">我是潘冠宇。北大普通生代表队队员、医学队长，<br class="desktop-break">全球卫生方向专硕研一。</p><div class="hero-tags"><span>篮球</span><span>ENTP</span><span>全球卫生</span></div><a class="button red" href="sports/">从球场认识我 <span>↗</span></a><p class="hero-aside">爱好多一点，生活就多几种打开方式。</p></div><figure class="hero-portrait">{img(205,eager=True)}<span class="portrait-stamp">ON &amp;<br>OFF<br>COURT.</span><figcaption><span>PAN GUANYU / 潘冠宇</span><span>生活，不止一面。</span></figcaption></figure></section>
<section class="wrap directory" id="explore"><div class="section-heading"><div><p class="eyebrow">PICK A SIDE</p><h2>你想先认识哪一面？</h2></div><p>五个入口，随意逛逛。</p></div><div class="directory-grid">
<a class="portal portal-sports" href="sports/"><div class="portal-photo">{img(208)}</div><div class="portal-copy"><span class="portal-index">01 / SPORTS</span><h3>球场见。</h3><p>篮球、腰旗橄榄球，与每一次上场。</p><span class="portal-arrow">↗</span></div></a>
<a class="portal portal-research" href="research/"><span class="portal-index">02 / RESEARCH</span><div class="research-glyph" aria-hidden="true">30 <i>→</i> 5</div><h3>认真研究。</h3><p>全球卫生 · 现场调查 · 数据实践</p><span class="portal-arrow">↗</span></a>
<a class="portal portal-photo-card" href="places/"><div class="portal-photo">{img(332)}</div><div class="portal-copy"><span class="portal-index">04 / PLACES</span><h3>出门看看。</h3><p>山野、水边，和城市里的光。</p><span class="portal-arrow">↗</span></div></a>
<a class="portal portal-me" href="me/"><span class="portal-index">03 / A LITTLE ABOUT ME</span><strong class="personality-type">ENTP<span>↗</span></strong><h3>还有这一面。</h3><p>一些爱好，几张旧照，和日常。</p><span class="portal-arrow">↗</span></a>
<a class="portal portal-photo-card portal-cat" href="pets/"><div class="portal-photo">{img(270)}</div><div class="portal-copy"><span class="portal-index">05 / PETS</span><h3>柠檬登场。</h3><p>猫咪，和路遇的小动物。</p><span class="portal-arrow">↗</span></div></a></div></section>'''

    sports = intro('sports','01 / SPORTS','上场，<br><em>就认真打。</em>','北大普通生代表队队员 · 医学队长<br>篮球之外，代表北大 Dragons 参加腰旗橄榄球比赛。')
    sports += f'<figure class="wrap chapter-cover sports-cover">{img(208,"../",True)}<figcaption><span>ON THE COURT</span><span>球场上的时间。</span></figcaption></figure>'
    sports += '''<section class="wrap records-section"><div class="section-heading"><div><p class="eyebrow">THE SCOREBOARD</p><h2>记在这里的成绩。</h2></div></div><div class="records-grid"><article class="record big"><span>2026 / 北大 3v3 超级联赛</span><h3>冠军 <i>&amp;</i> MVP</h3><p>团队冠军 · 个人最有价值球员</p></article><article class="record"><span>2026 / 代表北京大学</span><h3>四强</h3><p>澳门大学世界名校邀请赛</p></article><article class="record"><span>2026 / 北大 Dragons</span><h3>全国八强</h3><p>安德玛巅峰碗 · 腰旗橄榄球</p></article><article class="record campus-record"><span>校园篮球</span><h3>从新生杯到北大杯。</h3><p>2021 届北大新生杯冠军<br>2021—2024 届北大杯冠军</p></article></div><div class="hobby-line"><span>我的运动清单</span><p>篮球 / 攀岩 / 健身 / 腰旗橄榄球 / 滑雪</p></div></section>'''
    sports += gallery(['basketball','flag','training'],heading='比赛、训练，还有队友。')

    research = intro('research','02 / RESEARCH','把问题，<br><em>往深处想。</em>','北京大学 · 全球卫生方向专硕研一<br>本科专业背景：预防医学。')
    research += f'''<section class="wrap research-intro"><figure>{img(238,'../',True)}<figcaption>校园里的我。</figcaption></figure><div><p class="eyebrow">PUBLIC HEALTH / GLOBAL HEALTH</p><h2>从现场，到数据。</h2><p>我参与过健康政策资料整理、社区现场调查与数据清洗，也在医院和疾控中心实习过。目前在北京大学学习全球卫生。</p><div class="research-topics"><span>全球卫生</span><span>健康政策</span><span>社区调查</span><span>数据分析</span></div><a class="text-link" href="#work">看看我参与的工作 ↓</a></div></section>'''
    research += '''<section class="wrap research-project"><div><p class="eyebrow">DATA PROJECT / PYTHON</p><h2>变量少一点，<br>模型会怎样？</h2><p>用 WDBC 公开数据比较 30、10、5 个特征的逻辑回归模型。这是我学习 Python 时完成的课程项目：从数据检查、训练内特征选择，到独立测试和结果解释。</p><div class="actions"><a class="button red" href="../project/">打开交互项目 ↗</a><a class="text-link" href="https://github.com/aapan818-web/wdbc-feature-reduction" target="_blank" rel="noopener noreferrer">代码与报告 ↗</a></div></div><div class="feature-art" aria-label="比较30、10、5个输入特征"><span>FEATURES</span><div><b>30</b><i>→</i><b>10</b><i>→</i><b>5</b></div><p>特征减量 · 模型比较 · 可复现分析</p></div></section>
<section class="wrap research-work" id="work"><div class="section-heading"><div><p class="eyebrow">EXPERIENCE</p><h2>参与过的工作。</h2></div></div><div class="timeline"><article><time>2024.12 — 2025.07</time><div><h3>对非卫生援助的媒体报道研究</h3><p>参与非洲新闻媒体相关报道研究，负责数据筛选。</p></div></article><article><time>2024.07 — 2024.08</time><div><h3>北方农村常见慢性病家系队列</h3><p>参与现场研究，负责数据搜集与清洗。</p></div></article><article><time>2024.06 — 2024.07</time><div><h3>区域协同救援与远程医疗接受度</h3><p>参与暑期科研项目。</p></div></article><article><time>2024.02 — 2024.03</time><div><h3>关节、脊柱类医用耗材集中采购政策</h3><p>参与政策资料整理。</p></div></article></div><div class="experience-bottom"><div><p class="eyebrow">INTERNSHIPS</p><h3>医院与疾控实习</h3><p>北京海淀医院 · 2024.02—2025.01<br>深圳市疾病预防控制中心 · 2025.06—2025.09</p></div><div><p class="eyebrow">CAMPUS AWARD</p><h3>挑战杯 · 校级三等奖</h3><p>北京大学第 32 届挑战杯<br>五四青年科学奖</p></div></div></section>'''

    me = intro('me','03 / A LITTLE ABOUT ME','爱好有点多。<br><em>倒也不打算精简。</em>','潘冠宇 / ENTP<br>认真打球，也认真去玩。')
    me += f'''<section class="wrap me-intro"><div><p class="eyebrow">HELLO AGAIN</p><h2>名字三个字，<br>生活有很多面。</h2><p>我是潘冠宇。球场上是医学队长，课堂里学全球卫生，抖音里叫“潘潘潘冠冠”。篮球占了大学生活很大一部分，攀岩、健身、腰旗橄榄球、滑雪也都是我的爱好。</p><p>我喜欢出门看看，拍下山、海和城市，也拍猫。如果你也爱运动、旅行和猫，我们大概有得聊。</p><div class="me-labels"><span>ENTP</span><span>运动</span><span>旅行</span><span>猫</span></div></div><figure>{img(217,'../',True)}<figcaption>红墙前，留一张。</figcaption></figure></section>'''
    me += gallery(['me'],heading='从小时候，到现在。')

    places = intro('places','04 / PLACES & LIGHT','出门，<br><em>看看世界。</em>','山野、水边、城市、校园。<br>走过的路，留下的照片。')
    places += f'<figure class="wrap chapter-cover landscape-cover">{img(332,"../",True)}<figcaption><span>OUT THERE</span><span>山峰上的光。</span></figcaption></figure>'
    places += '<section class="wrap destinations"><p class="eyebrow">去过的地方</p><div>'+''.join(f'<span>{E(x)}</span>' for x in content['places'])+'</div></section>'
    places += gallery(['mountains','water','cities','campus'],heading='把风景收进相册。')

    pets = intro('pets','05 / PETS & LITTLE FRIENDS','这位，<br><em>叫柠檬。</em>','我的猫。<br>这一页，把镜头留给它。')
    pets += f'''<section class="wrap pet-intro"><figure class="pet-cover">{img(270,'../',True)}</figure><div><p class="eyebrow">MEET LEMON</p><h2>柠檬<span class="pet-dot">。</span></h2><p class="pet-subtitle">名字很酸，长得很甜。</p><p>沙发上、桌子下，或者抬头看人的时候。<br>日常里的几张柠檬。</p><a class="text-link" href="#gallery">看看它的照片 ↓</a></div></section>'''
    pets += gallery(['cats','animals'],heading='柠檬，和路上的小动物。')

    pages = {'':('认真打球，也认真去玩','潘冠宇的个人主页。篮球、全球卫生、旅行、生活与猫咪柠檬。',home,205),'sports':('运动','潘冠宇的运动记录、篮球与腰旗橄榄球比赛成绩和照片。',sports,208),'research':('科研与学习','潘冠宇的全球卫生学习、科研参与经历与公开数据项目。',research,238),'me':('性格与日常','潘冠宇，ENTP。爱好、童年照片与生活片刻。',me,217),'places':('旅行与风景','青甘大环线、北疆、大理、香格里拉和更多旅途中的照片。',places,332),'pets':('柠檬与小动物','潘冠宇的猫咪柠檬，以及旅行中遇见的小动物。',pets,270)}
    for slug,(title,description,body,cover) in pages.items():
        dest = directory / slug / 'index.html'
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(page(slug,title,description,body,cover))
    return list(pages)


if __name__ == '__main__':
    print('Built:', ', '.join(build_homepage()))
