# -*- coding: utf-8 -*-
"""扫描 BF_KJ 知识库 md -> 生成单文件零依赖交互式关系图谱 HTML（三类节点）。"""
import re, json, glob, os, html

ROOT = "/sandbox/workspace/BF_KJ"
KB = os.path.join(ROOT, "知识库")
OUT = os.path.join(ROOT, "保富法知识图谱.html")
REF = "/sandbox/workspace/HLM_KJ/红楼梦关系图谱.html"

TYPE_DIR = {"人物": "人物", "义理": "义理", "篇章": "篇章"}
COLOR = {"人物": "#3f5ea8", "义理": "#a9854f", "篇章": "#c96a3b"}
SOFT = {"人物": "#e7edfa", "义理": "#f5ecd9", "篇章": "#fbe9df"}
# 面板小标题文案
SUBTITLE = {
    "人物": "人物 · 史实例证",
    "义理": "义理 · 核心法则",
    "篇章": "篇章 · 原书结构",
}

def md_to_html(text):
    """轻量 md -> HTML：## h2, ### h3, - list, **bold**, [[wiki]], 段落。"""
    lines = text.split("\n")
    out, para, in_ul = [], [], False

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + "".join(para) + "</p>")
            para = []

    def flush_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def inline(s):
        s = html.escape(s, quote=False)
        # [[link]] -> wiki span
        s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: '<span class="wiki" data-id="%s">%s</span>' % (m.group(1), m.group(1)), s)
        # **bold**
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        return s

    for line in lines:
        raw = line.strip()
        if not raw:
            flush_para(); flush_ul(); continue
        if raw == "---":
            continue
        if raw.startswith("# "):
            continue  # 标题由面板 h1 显示
        if raw.startswith("## "):
            flush_para(); flush_ul()
            out.append("<h2>" + inline(raw[3:].strip()) + "</h2>")
        elif raw.startswith("### "):
            flush_para(); flush_ul()
            out.append("<h3>" + inline(raw[4:].strip()) + "</h3>")
        elif raw.startswith("- ") or raw.startswith("* "):
            flush_para()
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append("<li>" + inline(raw[2:].strip()) + "</li>")
        else:
            flush_ul()
            para.append(inline(raw) + " ")
    flush_para(); flush_ul()
    return "".join(out)

def get_summary(text, typ):
    """取第一个小节（身份/出处、含义、定位...）后的第一句作为导语。"""
    lines = text.split("\n")
    # 找第一个 ## 小节标题之后的正文段
    hit = False
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            if hit:
                break
            hit = True
            continue
        if hit and s and not s.startswith("#") and not s.startswith("- ") and s != "---":
            # 取到第一个句号/分号，限制长度
            s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
            s = re.sub(r"\*\*", "", s)
            cut = len(s)
            for p in ["。", "；", "，"]:
                i = s.find(p)
                if 0 < i < cut:
                    cut = i + 1
            if cut > 90:
                cut = 90
            return s[:cut].strip()
    return ""

def main():
    nodes = []
    id2idx = {}
    for typ, d in TYPE_DIR.items():
        for fp in sorted(glob.glob(os.path.join(KB, d, "*.md"))):
            tid = os.path.basename(fp)[:-3]
            raw = open(fp, encoding="utf-8").read()
            content = md_to_html(raw)
            summary = get_summary(raw, typ)
            nodes.append({"id": tid, "type": typ, "summary": summary, "content": content})
    for i, n in enumerate(nodes):
        id2idx[n["id"]] = i

    # 从 md 的 [[...]] 抽取边（无向、去重、只保留两端都在集合内）
    edges_set = set()
    for fp in glob.glob(os.path.join(KB, "*", "*.md")):
        src = os.path.basename(fp)[:-3]
        if src not in id2idx:
            continue
        raw = open(fp, encoding="utf-8").read()
        # 跳过 frontmatter 与 # 标题行中的链接（本库标题无链接，直接全取）
        for m in re.findall(r"\[\[([^\]]+)\]\]", raw):
            t = m.strip()
            if t in id2idx and t != src:
                a, b = id2idx[src], id2idx[t]
                edges_set.add((min(a, b), max(a, b)))
    edges = [{"s": a, "t": b} for a, b in sorted(edges_set)]

    # 度数
    deg = [0] * len(nodes)
    for e in edges:
        deg[e["s"]] += 1
        deg[e["t"]] += 1
    for i, n in enumerate(nodes):
        n["deg"] = deg[i]

    data = {"nodes": nodes, "edges": edges}
    payload = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))

    # 读取参考模板
    ref = open(REF, encoding="utf-8").read()

    # ---- 替换 DATA ----
    dm = re.search(r"const DATA\s*=\s*\{.*?\};\s*\n", ref, re.S)
    assert dm, "DATA not found"
    out = ref[:dm.start()] + "const DATA = " + payload + ";\n" + ref[dm.end():]

    # ---- 样式：补充三类配色变量与类 ----
    out = out.replace(
        "--event:#c96a3b; --event-soft:#fbe9df; --gold:#a9854f; --accent:#5c4326;",
        "--event:#c96a3b; --event-soft:#fbe9df; --yili:#a9854f; --yili-soft:#f5ecd9; --gold:#a9854f; --accent:#5c4326;")
    out = out.replace(".dot.p{background:var(--person)} .dot.e{background:var(--event)}",
                      ".dot.p{background:var(--person)} .dot.y{background:var(--yili)} .dot.e{background:var(--event)}")
    out = out.replace(".badge.p{background:var(--person-soft);color:var(--person)}\n.badge.e{background:var(--event-soft);color:var(--event)}",
                      ".badge.p{background:var(--person-soft);color:var(--person)}\n.badge.y{background:var(--yili-soft);color:var(--yili)}\n.badge.e{background:var(--event-soft);color:var(--event)}")
    out = out.replace(".chip.p{background:var(--person-soft);color:var(--person)} .chip.e{background:var(--event-soft);color:var(--event)}",
                      ".chip.p{background:var(--person-soft);color:var(--person)} .chip.y{background:var(--yili-soft);color:var(--yili)} .chip.e{background:var(--event-soft);color:var(--event)}")

    # ---- 文案：标题与按钮 ----
    out = out.replace("<title>红楼梦 · 关系图谱</title>", "<title>保富法 · 知识图谱</title>")
    out = out.replace('<span class="title-badge">紅樓夢</span>', '<span class="title-badge">保富法</span>')
    out = out.replace('<input id="search" placeholder="搜索人物 / 事件…">', '<input id="search" placeholder="搜索人物 / 义理 / 篇章…">')
    # 筛选按钮增加"义理"
    out = out.replace(
        '<button class="btn" data-f="人物">人物</button>\n        <button class="btn" data-f="事件">事件</button>',
        '<button class="btn" data-f="人物">人物</button>\n        <button class="btn" data-f="义理">义理</button>\n        <button class="btn" data-f="篇章">篇章</button>')
    out = out.replace(
        '<div class="card legend"><span><span class="dot p"></span>人物</span><span><span class="dot e"></span>事件</span></div>',
        '<div class="card legend"><span><span class="dot p"></span>人物</span><span><span class="dot y"></span>义理</span><span><span class="dot e"></span>篇章</span></div>')
    out = out.replace('<h1>红楼梦关系图谱</h1>', '<h1>保富法知识图谱</h1>')
    out = out.replace('<div class="sub">基于 Obsidian 知识库双向链接生成</div>', '<div class="sub">聂云台《保富法》· 基于双向链接生成</div>')

    # ---- JS 逻辑：三类着色 / 文案 ----
    out = out.replace('c.setAttribute("fill",n.type==="人物"?"#3f5ea8":"#c96a3b");',
                      'c.setAttribute("fill",n.type==="人物"?"#3f5ea8":n.type==="义理"?"#a9854f":"#c96a3b");')
    # subtitle
    out = out.replace('document.querySelector("#panel .sub").textContent=n.type==="人物"?"人物 · 贾府群像":"事件 · 原著情节";',
                      'document.querySelector("#panel .sub").textContent=SUBTITLE[n.type]||"";')
    # badge class
    out = out.replace("`<span class=\"badge ${n.type==='人物'?'p':'e'}\">${n.type}</span>`+",
                      "`<span class=\"badge ${n.type==='人物'?'p':n.type==='义理'?'y':'e'}\">${n.type}</span>`+")
    # chip class
    out = out.replace("<span class=\"chip ${idx[l].type==='人物'?'p':'e'}\" data-id=",
                      "<span class=\"chip ${idx[l].type==='人物'?'p':idx[l].type==='义理'?'y':'e'}\" data-id=")
    # overview 统计与标题、图例说明
    out = out.replace(
        'const pc=nodes.filter(n=>n.type==="人物").length,ec=N-pc;',
        'const pc=nodes.filter(n=>n.type==="人物").length,yc=nodes.filter(n=>n.type==="义理").length,ec=nodes.filter(n=>n.type==="篇章").length;')
    out = out.replace(
        'document.getElementById("stat").innerHTML=`共 <b>${N}</b> 个节点 · <b>${edges.length}</b> 条关系<br>人物 ${pc} · 事件 ${ec}`;',
        'document.getElementById("stat").innerHTML=`共 <b>${N}</b> 个节点 · <b>${edges.length}</b> 条关系<br>人物 ${pc} · 义理 ${yc} · 篇章 ${ec}`;')
    out = out.replace('document.querySelector("#panel h1").textContent="红楼梦关系图谱";',
                      'document.querySelector("#panel h1").textContent="保富法知识图谱";')
    out = out.replace('document.querySelector("#panel .sub").textContent="基于 Obsidian 知识库双向链接生成";',
                      'document.querySelector("#panel .sub").textContent="聂云台《保富法》· 基于双向链接生成";')
    out = out.replace(
        '点击任意节点，查看该人物 / 事件的 md 全文与关联。<br>节点越大关系越多；<span style="color:var(--person)">蓝=人物</span>，<span style="color:var(--event)">橙=事件</span>。',
        '点击任意节点，查看该页全文与关联。<br>节点越大关系越多；<span style="color:var(--person)">蓝=人物</span>，<span style="color:var(--yili)">金=义理</span>，<span style="color:var(--event)">橙=篇章</span>。')
    # 注入 SUBTITLE 常量（放在 NS 定义前）
    subconst = "const SUBTITLE=" + json.dumps(SUBTITLE, ensure_ascii=False) + ";\n"
    out = out.replace('const NS="http://www.w3.org/2000/svg";', subconst + 'const NS="http://www.w3.org/2000/svg";')

    open(OUT, "w", encoding="utf-8").write(out)

    # 自检报告
    typ_cnt = {t: sum(1 for n in nodes if n["type"] == t) for t in TYPE_DIR}
    print("节点", len(nodes), typ_cnt)
    print("边", len(edges))
    print("孤立节点", [n["id"] for n in nodes if n["deg"] == 0])
    print("度数TOP10", [(n["id"], n["deg"]) for n in sorted(nodes, key=lambda x: -x["deg"])[:10]])
    print("输出", OUT, os.path.getsize(OUT), "bytes")
    # 零依赖检查
    for pat in [r'<script[^>]+src=', r'<link[^>]+href=', r'@import', r'url\(\s*["\']?http']:
        print("依赖检查", pat, "命中", len(re.findall(pat, out)))

if __name__ == "__main__":
    main()
