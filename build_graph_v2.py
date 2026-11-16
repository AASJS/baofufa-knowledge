# -*- coding: utf-8 -*-
"""以【红楼梦改进版(可隐藏·沉浸阅读)】为模板，注入保富法 DATA，生成保富法新版交互式图谱。
完整继承：图谱宽度可调、可隐藏、沉浸阅读、阅读区居中限宽、移动端抽屉化、双指缩放/侧滑手势。
保留保富法：三类节点(人物/义理/篇章)、三类配色、全部文案。"""
import re, json, glob, os, html

ROOT = "/sandbox/workspace/BF_KJ"
KB = os.path.join(ROOT, "知识库")
OUT = os.path.join(ROOT, "保富法知识图谱.html")
REF = "/sandbox/workspace/uploads/红楼梦关系图谱.html"  # 改进版模板

TYPE_DIR = {"人物": "人物", "义理": "义理", "篇章": "篇章"}
SUBTITLE = {"人物": "人物 · 史实例证", "义理": "义理 · 核心法则", "篇章": "篇章 · 原书结构"}

def md_to_html(text):
    lines = text.split("\n")
    out, para, in_ul = [], [], False
    def flush_para():
        if para:
            out.append("<p>" + "".join(para) + "</p>"); para.clear()
    def flush_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>"); in_ul = False
    def inline(s):
        s = html.escape(s, quote=False)
        s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: '<span class="wiki" data-id="%s">%s</span>' % (m.group(1), m.group(1)), s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        return s
    for line in lines:
        raw = line.strip()
        if not raw or raw == "---":
            flush_para(); flush_ul(); continue
        if raw.startswith("# "):
            continue
        if raw.startswith("## "):
            flush_para(); flush_ul(); out.append("<h2>" + inline(raw[3:].strip()) + "</h2>")
        elif raw.startswith("### "):
            flush_para(); flush_ul(); out.append("<h3>" + inline(raw[4:].strip()) + "</h3>")
        elif raw.startswith("- ") or raw.startswith("* "):
            flush_para()
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append("<li>" + inline(raw[2:].strip()) + "</li>")
        else:
            flush_ul(); para.append(inline(raw) + " ")
    flush_para(); flush_ul()
    return "".join(out)

def get_summary(text):
    lines = text.split("\n"); hit = False
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            if hit: break
            hit = True; continue
        if hit and s and not s.startswith("#") and not s.startswith("- ") and s != "---":
            s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s); s = re.sub(r"\*\*", "", s)
            cut = len(s)
            for p in ["。", "；", "，"]:
                i = s.find(p)
                if 0 < i < cut: cut = i + 1
            return s[:min(cut, 90)].strip()
    return ""

def main():
    nodes, id2idx = [], {}
    for typ, d in TYPE_DIR.items():
        for fp in sorted(glob.glob(os.path.join(KB, d, "*.md"))):
            tid = os.path.basename(fp)[:-3]
            raw = open(fp, encoding="utf-8").read()
            nodes.append({"id": tid, "type": typ, "summary": get_summary(raw), "content": md_to_html(raw)})
    for i, n in enumerate(nodes): id2idx[n["id"]] = i

    edges_set = set()
    for fp in glob.glob(os.path.join(KB, "*", "*.md")):
        src = os.path.basename(fp)[:-3]
        if src not in id2idx: continue
        for m in re.findall(r"\[\[([^\]]+)\]\]", open(fp, encoding="utf-8").read()):
            t = m.strip()
            if t in id2idx and t != src:
                a, b = id2idx[src], id2idx[t]
                edges_set.add((min(a, b), max(a, b)))
    edges = [{"s": a, "t": b} for a, b in sorted(edges_set)]
    deg = [0] * len(nodes)
    for e in edges: deg[e["s"]] += 1; deg[e["t"]] += 1
    for i, n in enumerate(nodes): n["deg"] = deg[i]

    payload = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, separators=(", ", ": "))
    ref = open(REF, encoding="utf-8").read()

    # 1) 替换 DATA
    dm = re.search(r"const DATA\s*=\s*\{.*?\};\s*\n", ref, re.S)
    assert dm, "DATA not found"
    out = ref[:dm.start()] + "const DATA = " + payload + ";\n" + ref[dm.end():]

    # 2) 样式：补回保富法义理色变量与 .dot.y/.badge.y/.chip.y
    out = out.replace(
        "--event:#c96a3b; --event-soft:#fbe9df; --gold:#a9854f; --accent:#5c4326;",
        "--event:#c96a3b; --event-soft:#fbe9df; --yili:#a9854f; --yili-soft:#f5ecd9; --gold:#a9854f; --accent:#5c4326;")
    out = out.replace(".dot.p{background:var(--person)} .dot.e{background:var(--event)}",
                      ".dot.p{background:var(--person)} .dot.y{background:var(--yili)} .dot.e{background:var(--event)}")
    out = out.replace(".badge.p{background:var(--person-soft);color:var(--person)}\n.badge.e{background:var(--event-soft);color:var(--event)}",
                      ".badge.p{background:var(--person-soft);color:var(--person)}\n.badge.y{background:var(--yili-soft);color:var(--yili)}\n.badge.e{background:var(--event-soft);color:var(--event)}")
    out = out.replace(".chip.p{background:var(--person-soft);color:var(--person)} .chip.e{background:var(--event-soft);color:var(--event)}",
                      ".chip.p{background:var(--person-soft);color:var(--person)} .chip.y{background:var(--yili-soft);color:var(--yili)} .chip.e{background:var(--event-soft);color:var(--event)}")

    # 3) 标题 / 文案
    out = out.replace("<title>红楼梦 · 关系图谱（可隐藏 · 沉浸阅读）</title>", "<title>保富法 · 知识图谱（可隐藏 · 沉浸阅读）</title>")
    out = out.replace('<span class="title-badge">紅樓夢</span>', '<span class="title-badge">保富法</span>')
    out = out.replace('<input id="search" placeholder="搜索人物 / 事件…">', '<input id="search" placeholder="搜索人物 / 义理 / 篇章…">')
    # 三类筛选按钮
    out = out.replace(
        '<button class="btn" data-f="人物">人物</button>\n        <button class="btn" data-f="事件">事件</button>',
        '<button class="btn" data-f="人物">人物</button>\n        <button class="btn" data-f="义理">义理</button>\n        <button class="btn" data-f="篇章">篇章</button>')
    out = out.replace(
        '<div class="card legend"><span><span class="dot p"></span>人物</span><span><span class="dot e"></span>事件</span></div>',
        '<div class="card legend"><span><span class="dot p"></span>人物</span><span><span class="dot y"></span>义理</span><span><span class="dot e"></span>篇章</span></div>')
    out = out.replace('<h1>红楼梦关系图谱</h1>', '<h1>保富法知识图谱</h1>')
    out = out.replace('<div class="sub">基于 Obsidian 知识库双向链接生成</div>', '<div class="sub">聂云台《保富法》· 基于双向链接生成</div>')

    # 4) JS：三类着色 / 文案 / 统计
    out = out.replace('c.setAttribute("fill",n.type==="人物"?"#3f5ea8":"#c96a3b");',
                      'c.setAttribute("fill",n.type==="人物"?"#3f5ea8":n.type==="义理"?"#a9854f":"#c96a3b");')
    out = out.replace('document.querySelector("#panel .sub").textContent=n.type==="人物"?"人物 · 贾府群像":"事件 · 原著情节";',
                      'document.querySelector("#panel .sub").textContent=SUBTITLE[n.type]||"";')
    out = out.replace("`<span class=\"badge ${n.type==='人物'?'p':'e'}\">${n.type}</span>`+",
                      "`<span class=\"badge ${n.type==='人物'?'p':n.type==='义理'?'y':'e'}\">${n.type}</span>`+")
    out = out.replace("<span class=\"chip ${idx[l].type==='人物'?'p':'e'}\" data-id=",
                      "<span class=\"chip ${idx[l].type==='人物'?'p':idx[l].type==='义理'?'y':'e'}\" data-id=")
    out = out.replace('const pc=nodes.filter(n=>n.type==="人物").length,ec=N-pc;',
                      'const pc=nodes.filter(n=>n.type==="人物").length,yc=nodes.filter(n=>n.type==="义理").length,ec=nodes.filter(n=>n.type==="篇章").length;')
    out = out.replace('document.getElementById("stat").innerHTML=`共 <b>${N}</b> 个节点 · <b>${edges.length}</b> 条关系<br>人物 ${pc} · 事件 ${ec}`;',
                      'document.getElementById("stat").innerHTML=`共 <b>${N}</b> 个节点 · <b>${edges.length}</b> 条关系<br>人物 ${pc} · 义理 ${yc} · 篇章 ${ec}`;')
    out = out.replace('document.querySelector("#panel h1").textContent="红楼梦关系图谱";',
                      'document.querySelector("#panel h1").textContent="保富法知识图谱";')
    out = out.replace('document.querySelector("#panel .sub").textContent="基于 Obsidian 知识库双向链接生成";',
                      'document.querySelector("#panel .sub").textContent="聂云台《保富法》· 基于双向链接生成";')
    out = out.replace(
        '点击任意节点，查看该人物 / 事件的 md 全文与关联。<br>节点越大关系越多；<span style="color:var(--person)">蓝=人物</span>，<span style="color:var(--event)">橙=事件</span>。',
        '点击任意节点，查看该页全文与关联。<br>节点越大关系越多；<span style="color:var(--person)">蓝=人物</span>，<span style="color:var(--yili)">金=义理</span>，<span style="color:var(--event)">橙=篇章</span>。')
    # 注入 SUBTITLE 常量
    out = out.replace('const NS="http://www.w3.org/2000/svg";',
                      'const SUBTITLE=' + json.dumps(SUBTITLE, ensure_ascii=False) + ';\nconst NS="http://www.w3.org/2000/svg";')

    open(OUT, "w", encoding="utf-8").write(out)
    typ_cnt = {t: sum(1 for n in nodes if n["type"] == t) for t in TYPE_DIR}
    print("节点", len(nodes), typ_cnt, "| 边", len(edges))
    print("孤立节点", [n["id"] for n in nodes if n["deg"] == 0])
    print("输出", OUT, os.path.getsize(OUT), "bytes")
    for pat in [r'<script[^>]+src=', r'<link[^>]+href=', r'@import', r'url\(\s*["\']?http']:
        print("依赖检查", pat, "命中", len(re.findall(pat, out)))
    # 新版特性存在性检查
    for key in ["resizer", "hideGraphBtn", "showGraphBtn", "fabGraph", "scrim", "class=\"reader\"",
                "ph-inner", "graph-hidden", "pinch", "data-f=\"义理\"", "SUBTITLE"]:
        print("特性", key, "✓" if key in out else "✗ 缺失")

if __name__ == "__main__":
    main()
