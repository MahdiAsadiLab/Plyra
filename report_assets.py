"""Static CSS and JavaScript for the HTML dashboard.

Kept in its own file so the analysis code never contains page code. The
JavaScript only reads the JSON embedded in the page and writes text with
textContent (never innerHTML with data), so player names and comments cannot
inject HTML or scripts.
"""

CSS = r"""
:root{color-scheme:dark;--bg:#07131c;--panel:#0d1d28;--panel2:#122733;--line:#203b48;--text:#eaf1ed;--muted:#91a8b3;--muted2:#6f8995;--sage:#a8d0b8;--forest:#648a78;--ivory:#e9e0cb;--amber:#e8a85e;--red:#e56e70;--cyan:#69b8c4}
*{box-sizing:border-box}html{min-width:320px;background:var(--bg)}body{margin:0;color:var(--text);background:radial-gradient(ellipse at 50% -20%,#16303a 0,var(--bg) 55%);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;letter-spacing:.005em}header.top{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px clamp(16px,3vw,42px);border-bottom:1px solid var(--line);background:rgba(7,19,28,.9);box-shadow:0 8px 30px #0002}.brand-lockup{display:flex;align-items:center;gap:12px}.brand-mark{width:46px;height:46px;flex:0 0 46px;display:grid;place-items:center;border:1px solid #2c4a55;border-radius:13px;background:linear-gradient(145deg,#18323c,#091720);box-shadow:inset 0 1px #ffffff0c,0 5px 20px #0003}.brand-mark svg{width:32px;height:32px;display:block}.brand{font-family:Georgia,"Times New Roman",serif;font-size:27px;line-height:1;font-weight:700;letter-spacing:.01em}.brand span{color:var(--sage)}.brand-sub{margin-top:5px;color:var(--muted);font-size:10px;letter-spacing:.15em;text-transform:uppercase}.model{color:var(--muted);font-size:11px;text-align:right;line-height:1.7}main{width:min(1600px,100%);margin:0 auto;padding:22px clamp(12px,2.1vw,32px) 32px}.game-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 13px}.game-title{margin:0 0 4px;font-size:clamp(20px,2vw,28px);font-weight:650;letter-spacing:-.035em}.meta{color:var(--muted);font-size:11px;margin:0;display:flex;flex-wrap:wrap;gap:3px 0}.meta span+span:before{content:"·";color:var(--muted2);margin:0 9px}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:13px}.card{min-width:0;position:relative;overflow:hidden;background:linear-gradient(145deg,#142a35f5,#0c1c27fa);border:1px solid var(--line);border-radius:12px;padding:13px 16px;box-shadow:0 6px 22px #0002}.card:before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--sage);opacity:.72}.card .num{font-size:clamp(22px,2vw,29px);font-weight:700;line-height:1.08;letter-spacing:-.04em}.card .lbl{color:var(--muted);font-size:11px;margin-top:5px}.card .sub{color:var(--muted2);font-size:10px;margin-top:2px}.swatch{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px}.swatch.w{background:var(--ivory);border:1px solid #fff}.swatch.b{background:#526b70;border:1px solid #8ba2a6}.panel{min-width:0;background:linear-gradient(150deg,#0f212cfa,#0b1a24fa);border:1px solid var(--line);border-radius:13px;padding:15px;box-shadow:0 8px 26px #0002,inset 0 1px #ffffff04}.panel h2{margin:0 0 11px;font-size:12px;font-weight:650;letter-spacing:.025em;display:flex;align-items:center;gap:8px}.panel h2:before{content:"";width:3px;height:13px;border-radius:4px;background:var(--sage)}.graph-panel{margin-bottom:13px}.graph{width:100%;height:auto;display:block;background:linear-gradient(180deg,#0b1a24,#0b202a);border:1px solid #1a3440;border-radius:9px}.graph .axis{stroke:#25404b;stroke-width:1}.graph .mid{stroke:#3a5961;stroke-dasharray:4 5}.graph .area-w{fill:#83b8a030}.graph .area-b{fill:#0003}.graph .line{fill:none;stroke:#a8cdb8;stroke-width:2.2}.graph .cursor{stroke:var(--amber);stroke-width:1.5;display:none}.graph .pt{cursor:pointer}.graph text{fill:var(--muted);font-size:11px}.hint{color:var(--muted);font-size:10.5px;margin:7px 0 0}.layout{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.94fr) minmax(0,.94fr);gap:12px;align-items:stretch}.layout>*{min-width:0}.layout>.panel{height:100%;min-height:555px;min-width:0}.layout>.panel:first-child{display:flex;flex-direction:column}.board-wrap{position:relative;width:min(100%,560px);aspect-ratio:1;margin:0 auto;border:5px solid #122b35;border-radius:5px;overflow:hidden;box-shadow:0 12px 32px #0004}.board{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);width:100%;height:100%;user-select:none}.sq{position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.sq.l{background:var(--ivory)}.sq.d{background:var(--forest)}.sq.hl:after{content:"";position:absolute;inset:0;background:#efc4638c}.piece{position:relative;z-index:1;font-size:clamp(29px,3.7vw,55px);line-height:1;font-family:"DejaVu Sans","Noto Sans Symbols2","Segoe UI Symbol",serif;font-weight:600;transform:translateY(-1px);filter:drop-shadow(0 2px 1px #0004)}.piece.w{color:#fffdf2;-webkit-text-stroke:.45px #60766a;text-shadow:0 2px 1px #32453b,0 0 3px #fff8}.piece.b{color:#17251f;-webkit-text-stroke:.35px #e5e0cf;text-shadow:0 1px 0 #ffffff8a}.coord{position:absolute;z-index:2;font-size:9px;font-weight:700;opacity:.82;pointer-events:none}.sq.l .coord{color:#547365}.sq.d .coord{color:#f2ead7}svg.arrows{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:3}.controls{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:6px;margin-top:11px}button,select{max-width:100%;background:#142c38;color:var(--text);border:1px solid #2a4652;border-radius:8px;padding:7px 10px;font:inherit;font-size:11px;cursor:pointer;transition:background .15s,border-color .15s}button:hover,select:hover{background:#1a3944;border-color:#5d9382}button:active{transform:translateY(1px)}button:focus-visible,select:focus-visible,tr:focus-visible{outline:2px solid var(--sage);outline-offset:2px}button[aria-pressed=true]{background:#254d44;border-color:#6eaa93}.legend{color:var(--muted);font-size:10px;margin-top:auto;padding-top:10px}.legend i{display:inline-block;width:16px;height:0;border-top:3px solid;vertical-align:middle;margin:0 4px 0 8px}.legend i.best{border-color:var(--sage)}.legend i.played{border-color:var(--amber);border-top-style:dashed}.details{display:flex;flex-direction:column;height:100%}.details dl{display:grid;grid-template-columns:minmax(95px,auto) 1fr;gap:7px 10px;margin:12px 0 0;font-size:11px}.details dt{color:var(--muted)}.details dd{margin:0;overflow-wrap:anywhere;text-align:right}.details ul{margin:5px 0 0;padding-left:17px}.details .mono{font-family:ui-monospace,Consolas,monospace}.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:7px;font-weight:650;font-size:10px;white-space:nowrap;border:1px solid #ffffff12}.filters{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:9px;align-items:center}.filters label{color:var(--muted);font-size:10px}.filters label:first-child{display:inline-flex;align-items:center;gap:5px}.filters label:nth-child(2){display:none}#filter-errors{display:inline-block;padding:6px 9px}#filter-count{margin-left:auto;font-size:10px}.scroll{flex:1;min-height:0;max-height:435px;overflow:auto;border:1px solid #18303b;border-radius:8px}table.moves{border-collapse:separate;border-spacing:0;width:100%}table.moves th{position:sticky;top:0;background:#142c37;text-align:left;font-size:9px;color:var(--muted);padding:9px 6px;z-index:1;font-weight:600}table.moves td{padding:8px 6px;border-top:1px solid #27414c88;font-size:10.5px;vertical-align:middle}table.moves td:first-child{white-space:nowrap;color:var(--muted)}table.moves tr.mv{cursor:pointer}table.moves tr.mv:hover{background:#17313c}table.moves tr.mv.sel{background:#23483f}table.moves tr.hidden{display:none}table.moves td.n,table.moves th.n{text-align:right;font-variant-numeric:tabular-nums}.counts table{border-collapse:collapse;width:100%}.counts td,.counts th{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;font-size:11px}.counts td:first-child,.counts th:first-child{text-align:left}.counts th{color:var(--muted);font-weight:600}.settings,.warn{font-size:11px;color:var(--muted)}.settings li,.warn li{margin:4px 0}.note{background:#28261d;border:1px solid #655631;border-radius:9px;padding:11px 14px;margin:14px 0;font-size:11px}noscript .note{background:#342023;border-color:#6b3a3a}.empty{color:var(--muted);font-style:italic}footer{color:var(--muted2);font-size:10px;margin-top:22px;padding-top:13px;border-top:1px solid var(--line);text-align:center;letter-spacing:.08em}


/* Classification marks, persistent move tint, view switch and Neo-inspired pieces */
.sq .move-tag{position:absolute;z-index:4;top:2px;right:2px;display:grid;place-items:center;min-width:18px;height:18px;padding:0 3px;border-radius:4px;font-size:11px;font-weight:900;line-height:1;color:#fff;border:1px solid #ffffff55;box-shadow:0 1px 3px #0005}
.sq .move-tag.brilliant{background:#168a79}.sq .move-tag.great{background:#287bb7}.sq .move-tag.best{background:#2e9d50}.sq .move-tag.excellent{background:#4b8a68}.sq .move-tag.good{background:#8aa63c;color:#172016}.sq .move-tag.inaccuracy{background:#d49a3f;color:#211b16}.sq .move-tag.mistake{background:#e58c45;color:#211b16}.sq .move-tag.blunder,.sq .move-tag.miss{background:#d94e58}.sq .move-tag.book{background:#8d6e63}
.sq.last-destination{box-shadow:inset 0 0 0 100px #d8b84b35}.sq.last-origin{box-shadow:inset 0 0 0 100px #d8b84b22}
.details-switch{display:flex;align-items:center;gap:8px;margin:0 0 10px;color:var(--muted);font-size:11px}.details-switch select{font-size:11px}.classification-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.classification-item{display:flex;align-items:center;justify-content:space-between;gap:8px;border:1px solid var(--line);border-radius:8px;padding:8px;background:#102630;color:var(--text);text-align:left}.classification-item .class-mark{display:inline-grid;place-items:center;min-width:22px;height:22px;border-radius:5px;font-weight:900}.classification-item small{color:var(--muted)}
/* Neo-inspired Staunton silhouette using crisp chess glyphs and dimensional shading */
.piece{font-family:"DejaVu Sans","Noto Sans Symbols 2","Segoe UI Symbol",serif;font-size:clamp(30px,3.8vw,56px);font-weight:400;filter:drop-shadow(0 2px 1px #0006);line-height:1;transform:translateY(-1px)}
/* Plyra premium player header, engine candidates, and compact transport controls */
.cards{grid-template-columns:repeat(2,minmax(0,1fr));max-width:none;gap:12px}
.player-card{display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-rows:auto auto auto;align-items:center;column-gap:16px;position:relative;min-width:0;overflow:hidden;padding:15px 18px;border:1px solid var(--line);border-radius:13px;background:linear-gradient(135deg,#142a35f5,#0b1b26fa);box-shadow:0 6px 22px #0002}
.player-card:before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--sage)}.black-player:before{background:var(--amber)}
.player-side{grid-column:1;grid-row:1;color:var(--muted);font-size:10px;letter-spacing:.13em;font-weight:700}.player-name{grid-column:1;grid-row:2;font-size:clamp(15px,1.5vw,20px);font-weight:700;letter-spacing:-.02em;overflow-wrap:anywhere}.player-rating{grid-column:1;grid-row:3;color:var(--muted);font-size:11px}.player-accuracy{grid-column:2;grid-row:1/4;display:flex;align-items:center;gap:11px}.accuracy-ring{width:54px;height:54px;border-radius:50%;display:grid;place-items:center;border:4px solid #8db9a0;color:#eaf1ed;font-size:12px;font-weight:750;font-variant-numeric:tabular-nums;box-shadow:inset 0 0 0 3px #10232c}.black-ring{border-color:var(--amber)}.player-accuracy small{display:block;color:var(--muted);font-size:9px;letter-spacing:.12em}.player-accuracy strong{font-size:19px;line-height:1.4;font-variant-numeric:tabular-nums}
.game-head{align-items:center}.result-pill{padding:7px 15px;border:1px solid var(--line);border-radius:9px;background:#122733;color:var(--sage);font-weight:750;font-size:18px;white-space:nowrap}
.piece{font-family:"DejaVu Sans","Noto Sans Symbols 2","Segoe UI Symbol",serif;font-size:clamp(31px,4vw,57px);font-weight:400;filter:drop-shadow(0 2px 1px #0005);line-height:1;transform:translateY(-1px)}.piece.w{color:#fffdf4;-webkit-text-stroke:.25px #526b60;text-shadow:0 1px 0 #5b6c61,0 2px 2px #263b32,0 0 4px #fff9}.piece.b{color:#17221d;-webkit-text-stroke:.25px #d9d5c6;text-shadow:0 1px 0 #f3ecda,0 2px 2px #0004}
.controls{gap:5px;margin-top:12px;padding:7px;border:1px solid #1d3945;border-radius:12px;background:#091923;box-shadow:inset 0 1px #ffffff08}.controls button{min-width:31px;height:31px;padding:0 9px;border-radius:8px;font-size:12px;font-weight:700}.controls .nav-btn{background:linear-gradient(180deg,#193440,#10242f);border-color:#2b4652;color:#dbe8e1}.controls .primary-nav{background:linear-gradient(180deg,#386d5b,#244d42);border-color:#5b927c;color:#fff}.controls .utility-nav{margin-left:3px;color:var(--muted)}.nav-position{min-width:52px;text-align:center;color:#dbe8e1;font-size:10px;font-variant-numeric:tabular-nums}.engine-lines{margin-top:12px;padding:11px;border:1px solid #1c3945;border-radius:10px;background:linear-gradient(145deg,#102630,#0b1b25)}.engine-lines-head{display:flex;justify-content:space-between;gap:8px;align-items:baseline;margin-bottom:8px}.engine-lines-head strong{font-size:11px}.engine-lines-head span{font-size:9px;color:var(--muted)}.candidate-list{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}.candidate-btn{min-width:0;display:flex;flex-direction:column;align-items:center;gap:3px;padding:7px 3px;border-radius:7px;background:#142e39;border:1px solid #284652;color:var(--text)}.candidate-btn strong{font-size:12px;overflow-wrap:anywhere}.candidate-btn small{font-size:9px;color:var(--muted);font-variant-numeric:tabular-nums}.candidate-btn[aria-pressed=true]{background:#245044;border-color:#83b8a0;box-shadow:inset 0 0 0 1px #83b8a044}.candidate-btn:first-child strong{color:#a8d0b8}.candidate-btn:disabled{opacity:.45;cursor:not-allowed}
.details-panel{background:linear-gradient(150deg,#102630,#0b1a24)}.details summary{background:linear-gradient(100deg,#142e39,#0d202b);border-radius:12px}.details[open] summary{border-bottom:1px solid var(--line);border-radius:12px 12px 0 0}.details #details-body{padding:14px 16px 17px}.details #details-body>div:first-child{display:flex;align-items:center;flex-wrap:wrap;gap:7px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--line)}.details dl{gap:9px 12px;font-size:11px}.details dt{line-height:1.45}.details dd{font-weight:600;color:#dce9e2}.details dd .mono{overflow-wrap:anywhere}.details ul{color:var(--muted);text-align:left}.summary-hint{letter-spacing:.02em}
@media(max-width:760px){.cards{grid-template-columns:minmax(0,1fr)}.player-card{padding:12px 14px}.accuracy-ring{width:47px;height:47px}.player-accuracy strong{font-size:16px}.candidate-list{grid-template-columns:repeat(3,minmax(0,1fr))}.controls{flex-wrap:nowrap}.controls .utility-nav{margin-left:0}.nav-position{min-width:36px}.game-head{gap:8px}.result-pill{font-size:14px;padding:5px 10px}}

/* Premium score-sheet, move badges and optional details */
.cards{grid-template-columns:repeat(2,minmax(0,1fr));max-width:520px}
.layout{grid-template-columns:minmax(0,1.03fr) minmax(0,.72fr) minmax(0,1fr);align-items:stretch}
.layout>.panel{min-height:540px}
.move-sheet-scroll{max-height:560px}
table.move-sheet{table-layout:fixed}
table.move-sheet th{font-size:10px;letter-spacing:.11em;padding:11px 10px}
table.move-sheet th.move-number{width:42px;text-align:right}
table.move-sheet td.move-cell{position:relative;padding:9px 10px;cursor:pointer;border-left:1px solid #27414c66}
table.move-sheet td.move-cell:hover{background:#1b3943}
table.move-sheet td.move-cell.sel{background:#23483f;box-shadow:inset 0 0 0 1px #568b77}
.move-san{font-size:13px;font-weight:700;display:inline-block;max-width:calc(100% - 38px);overflow:hidden;text-overflow:ellipsis;vertical-align:middle}
.move-acc{float:right;color:var(--muted);font-size:10px;font-variant-numeric:tabular-nums;margin-left:5px}
.move-class{display:block;margin-top:3px}
.move-class .badge{font-size:9px;padding:1px 5px;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.move-number{font-size:11px;color:var(--muted);font-weight:500;text-align:right;background:#0c1a24}
.empty-cell{color:var(--muted2);text-align:center}
.details-panel{padding:0!important;min-height:0!important;align-self:start}
.details summary{list-style:none;cursor:pointer;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px}
.details summary::-webkit-details-marker{display:none}
.details summary:after{content:'＋';color:var(--sage);font-size:16px}
.details[open] summary:after{content:'−'}
.summary-title{font-size:12px;font-weight:650}.summary-title:before{content:'';display:inline-block;width:3px;height:13px;border-radius:4px;background:var(--sage);margin-right:9px;vertical-align:-2px}
.summary-hint{margin-left:auto;color:var(--muted);font-size:10px}
.details #details-body{padding:0 16px 16px}
.details dl{grid-template-columns:minmax(85px,auto) 1fr}
.sq .move-tag{position:absolute;right:2px;top:2px;z-index:4;max-width:calc(100% - 4px);padding:1px 3px;border-radius:4px;background:#0b1c25e8;color:#f4f1e8;font:700 clamp(6px,.65vw,9px)/1.25 ui-sans-serif,system-ui,sans-serif;letter-spacing:-.02em;white-space:nowrap;box-shadow:0 1px 4px #0005}
.sq .move-tag.blunder{background:#a93f48}.sq .move-tag.mistake{background:#b46a36}.sq .move-tag.inaccuracy{background:#94702f}.sq .move-tag.great,.sq .move-tag.brilliant{background:#237e70}
@media(max-width:1180px){.layout{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.layout>.panel:first-child{grid-row:span 2}.movelist-panel{grid-column:2}.details-panel{grid-column:2;grid-row:2}.piece{font-size:min(5vw,48px)}}
@media(max-width:760px){.cards{grid-template-columns:repeat(2,minmax(0,1fr));max-width:none}.layout{grid-template-columns:minmax(0,1fr)}.layout>.panel:first-child{grid-row:auto}.movelist-panel,.details-panel{grid-column:auto;grid-row:auto}.move-san{font-size:12px}.move-sheet-scroll{max-height:420px}.summary-hint{display:none}}

@media(max-width:1180px){.layout{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.layout>.panel{min-height:500px}.layout>.panel:first-child{grid-row:span 2}.movelist-panel{grid-column:2}.piece{font-size:min(5vw,48px)}}@media(max-width:760px){header.top{padding:13px 15px;align-items:flex-start}.model{display:none}main{padding:14px 10px 24px}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.card{padding:12px;border-radius:10px}.layout{grid-template-columns:minmax(0,1fr);gap:10px}.layout>.panel,.layout>.panel:first-child{min-height:0;grid-row:auto}.movelist-panel{grid-column:auto}.board-wrap{width:min(100%,520px)}.piece{font-size:min(10vw,48px)}.scroll{max-height:360px}.game-head{display:block}}
/* Final Plyra dashboard refinements */
.cards{grid-template-columns:repeat(2,minmax(0,1fr));max-width:none;width:100%;gap:14px}
.player-card{min-height:104px;grid-template-columns:minmax(0,1fr) auto;column-gap:20px;padding:17px 22px}
.player-name{font-size:clamp(16px,1.7vw,22px)}
.player-accuracy{gap:13px}.accuracy-ring{width:58px;height:58px;font-size:13px}.player-accuracy strong{font-size:21px}
.layout{grid-template-columns:minmax(0,1.03fr) minmax(0,.82fr) minmax(0,1fr);align-items:start}
.layout>.panel{min-height:0;height:auto}
.layout>.panel:first-child{align-self:start}
.movelist-panel{display:flex;flex-direction:column;gap:0}
.move-sheet-scroll{max-height:340px;flex:0 0 auto}
.graph-in-moves{margin-top:12px;padding:10px 11px 9px;border-radius:10px;background:linear-gradient(150deg,#0c1d27,#0a1821);border-color:#1a3440}
.graph-in-moves h2{font-size:11px;margin-bottom:7px}.graph-in-moves .graph{max-height:145px}.graph-in-moves .hint{font-size:9px;margin-top:4px}
.board-stage{display:grid;grid-template-columns:25px minmax(0,1fr);gap:7px;align-items:stretch;width:100%;max-width:590px;margin:0 auto}
.board-wrap{width:100%;max-width:none;min-width:0}
.eval-bar{position:relative;overflow:hidden;border-radius:4px;border:1px solid #33464b;background:#17252b;min-height:100%;display:flex;align-items:center;justify-content:center}
.eval-bar:before{content:"";position:absolute;left:0;right:0;top:50%;border-top:1px solid #dce8df66;z-index:2}
.eval-bar span{position:absolute;bottom:50%;left:0;right:0;height:0;background:linear-gradient(180deg,#eee5d2,#a8cbb5);transition:height .15s,bottom .15s}
.eval-bar strong{position:absolute;z-index:3;left:50%;top:6px;writing-mode:vertical-rl;transform:translateX(-50%);font-size:8px;letter-spacing:-.02em;color:#f4f1e8;text-shadow:0 1px 3px #000;background:#07131ccc;padding:3px 2px;border-radius:3px;white-space:nowrap}
/* Warm, carved-wood-inspired piece rendering using system chess glyphs */
.piece{font-family:"DejaVu Sans","Noto Sans Symbols 2","Segoe UI Symbol",serif;font-size:clamp(30px,3.8vw,56px);font-weight:400;line-height:1;transform:translateY(-1px);filter:drop-shadow(0 2px 1px #0005);-webkit-text-stroke:.35px #35271d}
.piece.w{color:#f4e5c6;text-shadow:0 1px 0 #fff7e8,0 2px 1px #8a6b47,0 3px 2px #273a30;background:linear-gradient(115deg,#fff1cf 4%,#e6c995 35%,#fff2d5 56%,#b58c5d 88%);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.piece.b{color:#4d3020;text-shadow:0 1px 0 #d8b17b,0 2px 2px #0008;background:linear-gradient(115deg,#a77749 2%,#4c2d1d 32%,#8b5a35 58%,#342016 88%);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;-webkit-text-stroke:.5px #d3b082}
.sq.hl:after{background:rgba(239,196,99,.36);box-shadow:inset 0 0 0 2px #e8bd59}
.sq .move-tag{right:2px;top:2px;z-index:4;width:19px;height:19px;max-width:none;display:grid;place-items:center;padding:0;border-radius:4px;background:#2d8d76;color:#fff;font:800 12px/1 ui-sans-serif,system-ui,sans-serif;box-shadow:0 1px 4px #0006}
.sq .move-tag.brilliant,.sq .move-tag.great{background:#168a79}.sq .move-tag.best,.sq .move-tag.excellent,.sq .move-tag.good{background:#4b8a68}.sq .move-tag.inaccuracy{background:#d49a3f;color:#1d211d}.sq .move-tag.mistake{background:#e58c45;color:#211b16}.sq .move-tag.blunder,.sq .move-tag.miss{background:#d94e58}
.controls{gap:4px;margin-top:10px;padding:6px}.controls button{min-width:29px;width:31px;height:30px;padding:0;font-size:11px}.controls .utility-nav{width:auto;min-width:38px;padding:0 7px}.nav-position{min-width:65px;font-size:10px}
@media(max-width:1180px){.layout{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.layout>.panel{min-height:0}.layout>.panel:first-child{grid-row:auto}.details-panel{grid-column:2;grid-row:2}.movelist-panel{grid-column:1 / -1;grid-row:3}.move-sheet-scroll{max-height:300px}.graph-in-moves .graph{max-height:170px}}
@media(max-width:760px){.cards{grid-template-columns:minmax(0,1fr);gap:8px}.player-card{padding:12px 14px;min-height:88px}.accuracy-ring{width:48px;height:48px}.player-accuracy strong{font-size:17px}.layout{grid-template-columns:minmax(0,1fr)}.layout>.panel:first-child,.details-panel,.movelist-panel{grid-column:auto;grid-row:auto}.board-stage{grid-template-columns:22px minmax(0,1fr)}.piece{font-size:min(10vw,48px)}.move-sheet-scroll{max-height:300px}.graph-in-moves .graph{max-height:150px}}


/* Chess.com-inspired move classification, compact desktop dashboard and stable mobile navigation */
.sq.last-origin,.sq.last-destination{box-shadow:inset 0 0 0 100px var(--move-class-bg,rgba(138,166,160,.2));outline:1px solid var(--move-class-color,#8aa6a0);outline-offset:-1px}
.sq .move-tag{min-width:19px;height:19px;padding:0 3px;border:1px solid #ffffff8c;box-shadow:0 1px 3px #0006;text-shadow:0 1px 1px #0005}
.board,.board-wrap,.controls{touch-action:manipulation}.move-sheet-scroll,.scroll{overscroll-behavior:contain;overflow-anchor:none}
#details-view{margin-left:auto}.classification-summary{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.classification-item{padding:6px 8px}.classification-item:disabled{opacity:.48;cursor:default}
@media(min-width:1181px) and (min-height:760px){main{padding-top:10px;padding-bottom:12px}.game-head{margin-bottom:8px}.cards{gap:7px;margin-bottom:8px}.card{padding:9px 12px}.card .num{font-size:23px}.layout{gap:9px}.layout>.panel{min-height:0}.board-wrap{width:min(100%,calc(100vh - 330px),520px)}.panel{padding:11px}.move-sheet-scroll{max-height:calc(100vh - 360px)}.graph-in-moves .graph{max-height:145px}.graph-panel{margin-bottom:6px}}
@media(max-width:760px){html,body{overflow-anchor:none}.layout{scroll-margin:0}.board-wrap{width:min(100%,calc(100vw - 48px));}.controls{gap:4px}.controls button{padding:7px 8px}.classification-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.details-panel{scroll-margin:0}.move-sheet-scroll{max-height:300px}}


/* Final visual pass: monochrome pieces, Chess.com-like evaluation bar and compact classification table */
.eval-bar{background:#fff;border-color:#30343a;border-radius:3px}
.eval-bar:before{display:none}
.eval-bar span{left:0;right:0;bottom:auto;border-radius:0;transition:height .18s ease}
.eval-bar strong{writing-mode:vertical-rl;top:50%;transform:translate(-50%,-50%);background:#202328;color:#fff;font-size:8px}
.piece{font-family:"DejaVu Sans","Noto Sans Symbols 2","Segoe UI Symbol",serif;font-weight:400;filter:drop-shadow(0 1px 1px #0005);background:none!important;background-clip:border-box!important;-webkit-background-clip:border-box!important;-webkit-text-fill-color:currentColor!important;-webkit-text-stroke:0!important}
.piece.w{color:#fff!important;text-shadow:0 1px 1px #111,0 0 1px #111!important}
.piece.b{color:#111!important;text-shadow:0 0 1px #fff,0 1px 1px #fff8!important}
.sq.l{background:#f0f0f0}.sq.d{background:#779656}
.player-accuracy{position:relative;display:flex;align-items:center;justify-content:center;gap:0}
.accuracy-ring{width:58px;height:58px;flex:0 0 58px;border-radius:50%;display:grid;place-items:center;font-size:13px;font-weight:750;line-height:1;color:#f5f7f8;border:4px solid #8db9a0;background:#10232c;box-shadow:inset 0 0 0 3px #10232c}
.black-ring{border-color:#e8a85e}
.accuracy-label{position:absolute;top:calc(100% + 2px);font-size:8px;letter-spacing:.1em;color:var(--muted);white-space:nowrap}
.classification-summary{display:block}
.classification-table{width:100%;border-collapse:collapse;border-spacing:0}
.classification-table th{padding:7px 8px;color:var(--muted);font-size:10px;font-weight:600;text-align:left;border-bottom:1px solid var(--line)}
.classification-table th.n,.classification-table td.n{text-align:right;font-variant-numeric:tabular-nums}
.classification-table td{padding:5px 8px;border-bottom:1px solid #203b4888;font-size:11px}
.classification-table td:first-child{display:flex;align-items:center;gap:8px}
.classification-table tr[role=button]{cursor:pointer}
.classification-table tr[role=button]:hover{background:#17313c}
.class-badge{display:inline-grid;place-items:center;min-width:24px;height:22px;padding:0 5px;border-radius:6px;color:#fff;font-weight:850;font-size:11px;line-height:1}
.class-badge.brilliant{background:#168a79}.class-badge.great{background:#287bb7}.class-badge.best{background:#2e8b3d}.class-badge.excellent{background:#4b8a35}.class-badge.good{background:#8aa63c;color:#172016}.class-badge.book{background:#8d6e63}.class-badge.inaccuracy{background:#f9a825;color:#1a1a1a}.class-badge.mistake{background:#f07819}.class-badge.miss,.class-badge.blunder{background:#c62828}.class-badge.unclassified{background:#667780}
@media(max-width:760px){.accuracy-ring{width:48px;height:48px;flex-basis:48px}.player-accuracy{justify-content:flex-start}.accuracy-label{font-size:8px}}

"""

JS = r"""
(function () {
  "use strict";
  var raw = document.getElementById("plyra-data");
  if (!raw) { return; }
  var DATA;
  try { DATA = JSON.parse(raw.textContent); } catch (e) { return; }
  var MOVES = DATA.moves, STYLE = DATA.label_style;
  var GLYPH = { k:"\u265A", q:"\u265B", r:"\u265C", b:"\u265D", n:"\u265E", p:"\u265F" };
  var TEXT_VS = "\uFE0E";
  var NS = "http://www.w3.org/2000/svg";
  var state = { ply: 0, mode: "after", flipped: false, side: "both", label: "all", errorsOnly: false, candidateUci: null };

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) { n.className = cls; }
    if (text !== undefined && text !== null) { n.textContent = text; }
    return n;
  }
  function svgEl(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) { n.setAttribute(k, attrs[k]); }
    return n;
  }

  /* ---------- FEN parsing and board drawing ---------- */
  function parseFen(fen) {
    var rows = fen.split(" ")[0].split("/"), board = [];
    for (var r = 0; r < 8; r++) {
      var row = [], text = rows[r] || "";
      for (var i = 0; i < text.length; i++) {
        var c = text[i];
        if (c >= "1" && c <= "8") { for (var k = 0; k < +c; k++) { row.push(null); } }
        else { row.push(c); }
      }
      while (row.length < 8) { row.push(null); }
      board.push(row);
    }
    return board;
  }
  function squareIndex(name) {  /* "e4" -> {file:4, rank:3} (rank 0 = rank 1) */
    return { file: name.charCodeAt(0) - 97, rank: +name[1] - 1 };
  }
  function boardCoords(file, rank) {  /* -> column,row on screen (0..7) honouring flip */
    return state.flipped ? { c: 7 - file, r: rank } : { c: file, r: 7 - rank };
  }
  function currentFen() {
    if (state.ply === 0) { return DATA.start_fen; }
    var m = MOVES[state.ply - 1];
    return state.mode === "before" ? m.fen_before : m.fen_after;
  }
  function drawArrow(svg, uci, color, dashed) {
    if (!uci || uci.length < 4) { return; }
    var a = squareIndex(uci.slice(0, 2)), b = squareIndex(uci.slice(2, 4));
    var p = boardCoords(a.file, a.rank), q = boardCoords(b.file, b.rank);
    var x1 = p.c + .5, y1 = p.r + .5, x2 = q.c + .5, y2 = q.r + .5;
    var dx = x2 - x1, dy = y2 - y1, len = Math.sqrt(dx * dx + dy * dy) || 1;
    var ux = dx / len, uy = dy / len, head = .32;
    var ex = x2 - ux * head, ey = y2 - uy * head;
    var attrs = { x1: x1, y1: y1, x2: ex, y2: ey, stroke: color, "stroke-width": .16, "stroke-linecap": "round", opacity: .85 };
    if (dashed) { attrs["stroke-dasharray"] = ".3 .22"; }
    svg.appendChild(svgEl("line", attrs));
    var px = -uy, py = ux;
    var pts = [x2, y2, ex + px * .2, ey + py * .2, ex - px * .2, ey - py * .2].join(",");
    svg.appendChild(svgEl("polygon", { points: pts, fill: color, opacity: .9 }));
  }
  function classificationMark(label) {
    return ({Brilliant:"!!",Great:"!",Best:"★",Excellent:"✓",Good:"○",Book:"B",Inaccuracy:"!?",Mistake:"?",Miss:"×",Blunder:"??",Unclassified:"–"})[label] || "!?";
  }
  function hexToRgba(hex, alpha) {
    var h = String(hex || "#8aa6a0").replace("#", "");
    if (h.length === 3) h = h.split("").map(function(c){return c+c;}).join("");
    var n = parseInt(h.slice(0,6), 16);
    if (!isFinite(n)) return "rgba(138,166,160," + alpha + ")";
    return "rgba(" + ((n>>16)&255) + "," + ((n>>8)&255) + "," + (n&255) + "," + alpha + ")";
  }
  function renderBoard() {
    var host = $("board"), arrows = $("arrows");
    if (!host) { return; }
    var grid = parseFen(currentFen()), move = state.ply ? MOVES[state.ply - 1] : null;
    var marked = {};
    if (move && state.mode === "after") {
      marked[move.uci.slice(0, 2)] = "last-origin"; marked[move.uci.slice(2, 4)] = "last-destination";
    }
    var moveStyle = move ? (STYLE[move.label] || STYLE.Unclassified) : null;
    var classColor = moveStyle && moveStyle[0] ? moveStyle[0] : "#8aa6a0";
    host.textContent = "";
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        var file = state.flipped ? 7 - c : c, rank = state.flipped ? r : 7 - r;
        var name = String.fromCharCode(97 + file) + (rank + 1);
        var sq = el("div", "sq " + ((file + rank) % 2 === 0 ? "d" : "l") + (marked[name] ? " " + marked[name] : ""));
        sq.setAttribute("data-square", name);
        if (marked[name] && moveStyle) {
          sq.style.setProperty("--move-class-color", classColor);
          sq.style.setProperty("--move-class-bg", hexToRgba(classColor, marked[name] === "last-destination" ? 0.30 : 0.17));
        }
        var piece = grid[7 - rank][file];
        if (piece) {
          var lower = piece.toLowerCase();
          sq.appendChild(el("span", "piece " + (piece === lower ? "b" : "w"), GLYPH[lower] + TEXT_VS));
        }
        if (move && state.mode === "after" && name === move.uci.slice(2, 4)) {
          var tag = el("span", "move-tag " + String(move.label || "").toLowerCase(), classificationMark(move.label));
          tag.style.background = classColor;
          tag.style.color = (moveStyle && moveStyle[1]) || "#fff";
          tag.setAttribute("title", move.label + " move"); tag.setAttribute("aria-label", move.label + " move"); sq.appendChild(tag);
        }
        if (c === 0) { sq.appendChild(el("span", "coord r", String(rank + 1))); }
        if (r === 7) { sq.appendChild(el("span", "coord f", String.fromCharCode(97 + file))); }
        host.appendChild(sq);
      }
    }
    arrows.textContent = "";
    if (state.candidateUci && move) {
      drawArrow(arrows, state.candidateUci, "#83b8a0", false);
    } else if (move && state.mode === "before") {
      if (move.best_uci && move.best_uci !== move.uci) { drawArrow(arrows, move.best_uci, "#3fb950", false); }
      drawArrow(arrows, move.uci, "#e5534b", move.best_uci !== move.uci);
    }
    var evalCp = move ? (state.mode === "before" ? null : move.eval_cp) : null;
    var evalMate = move && state.mode !== "before" ? move.eval_mate : null;
    var evalValue = $("eval-value"), evalFill = $("eval-fill");
    if (evalValue) {
      if (evalMate !== null && evalMate !== undefined) evalValue.textContent = (evalMate > 0 ? "+M" : "−M") + Math.abs(evalMate) + " · White";
      else if (evalCp !== null && evalCp !== undefined) evalValue.textContent = (evalCp > 0 ? "+" : "") + (evalCp / 100).toFixed(2) + " · White";
      else evalValue.textContent = "White POV";
    }
    if (evalFill) {
      var score = evalCp === null || evalCp === undefined ? 0 : Math.max(-800, Math.min(800, evalCp));
      /* eval_cp is normalized to White's POV in reports.py. Keep the bar's
         orientation fixed: Black always occupies the top, White the bottom.
         White advantage moves the boundary upward; Black advantage downward. */
      var blackPercent = Math.max(0, Math.min(100, 50 - score / 16));
      evalFill.style.top = "0";
      evalFill.style.bottom = "auto";
      evalFill.style.height = blackPercent + "%";
      evalFill.style.background = "#17191c";
      evalFill.title = "Evaluation from White’s perspective; positive favours White";
    }
    $("board-caption").textContent = !move ? "Starting position" :
      (state.mode === "before" ? "Before " : "After ") + move.label_text + " " + move.san;
  }

  /* ---------- details panel ---------- */
  function badge(label) {
    var s = STYLE[label] || STYLE.Unclassified;
    var b = el("span", "badge", s[2] + " " + label);
    b.style.background = s[0]; b.style.color = s[1];
    return b;
  }
  function addRow(dl, term, valueNode) {
    dl.appendChild(el("dt", null, term));
    var dd = el("dd");
    if (typeof valueNode === "string") { dd.textContent = valueNode; } else { dd.appendChild(valueNode); }
    dl.appendChild(dd);
  }
  function listNode(items) {
    var ul = el("ul");
    items.forEach(function (t) { ul.appendChild(el("li", null, t)); });
    return ul;
  }
  function renderDetails() {
    var view = $("details-view") ? $("details-view").value : "details";
    var box = $("details-body"), classBox = $("classification-body");
    if (box) box.hidden = view !== "details";
    if (classBox) classBox.hidden = view !== "classifications";
    if (view === "classifications") { renderClassificationSummary(); return; }
    box.textContent = "";
    if (!state.ply) {
      box.appendChild(el("p", "empty", "Select a move in the list or on the graph. Arrow keys move through the game."));
      return;
    }
    var m = MOVES[state.ply - 1];
    var head = el("div");
    head.appendChild(el("strong", null, m.label_text + " \u2014 " + m.color + ": "));
    head.appendChild(el("span", "mono", m.san));
    head.appendChild(document.createTextNode(" "));
    head.appendChild(badge(m.label));
    box.appendChild(head);
    var dl = el("dl");
    addRow(dl, "Played", m.san + "  (" + m.uci + ")");
    addRow(dl, "Engine's best", m.best_san ? m.best_san + "  (" + (m.best_uci || "") + ")" : "not available");
    addRow(dl, "Best-move eval", (m.best_text || "n/a") + "  (White's view)");
    addRow(dl, "After played move", (m.played_text || "n/a") + "  (White's view)");
    addRow(dl, "Accuracy", m.accuracy === null ? "not scored" : m.accuracy.toFixed(1) + " / 100");
    addRow(dl, "Win% (mover)", m.win_before === null || m.win_after === null ? "n/a" :
      m.win_before.toFixed(1) + "% \u2192 " + m.win_after.toFixed(1) + "%");
    addRow(dl, "Expected points", m.ep_before === null ? "n/a" :
      m.ep_before.toFixed(2) + " \u2192 " + m.ep_played.toFixed(2) + "  (loss " + m.ep_loss.toFixed(3) + ")");
    addRow(dl, "Centipawn loss", m.loss_cp === null ? "n/a (forced mate involved or no data)" : m.loss_cp + " cp (" + (m.loss_cp / 100).toFixed(2) + " pawns)");
    if (m.best_line.length) { addRow(dl, "Best line", (function () { var s = el("span", "mono", m.best_line.join(" ")); return s; })()); }
    if (m.played_line.length) { addRow(dl, "After the played move", (function () { return el("span", "mono", m.played_line.join(" ")); })()); }
    if (m.candidates.length) { addRow(dl, "Candidates", m.candidates.join(",  ")); }
    if (m.annotations.length) { addRow(dl, "Annotations", listNode(m.annotations)); }
    if (m.explanation.length) { addRow(dl, "Why this label", listNode(m.explanation)); }
    if (m.note) { addRow(dl, "Note", m.note); }
    if (m.confidence === "low") { addRow(dl, "Confidence", "low (the evaluation was unstable)"); }
    box.appendChild(dl);
  }

  function renderClassificationSummary() {
    var host = $("classification-body"); if (!host) return;
    host.textContent = "";
    var labels = ["Brilliant","Great","Best","Excellent","Good","Book","Inaccuracy","Mistake","Miss","Blunder","Unclassified"];
    var counts = {};
    labels.forEach(function(label){ counts[label] = {White:0,Black:0}; });
    MOVES.forEach(function(m){
      var label = m.label || "Unclassified";
      if (!counts[label]) counts[label] = {White:0,Black:0};
      counts[label][String(m.color || "White").toLowerCase() === "black" ? "Black" : "White"]++;
    });
    var table = el("table", "classification-table");
    var thead = el("thead"), head = el("tr");
    ["Class", "White", "Black"].forEach(function(name, i){ head.appendChild(el("th", i ? "n" : "", name)); });
    thead.appendChild(head); table.appendChild(thead);
    var body = el("tbody");
    labels.forEach(function(label){
      var c = counts[label] || {White:0,Black:0};
      if (!c.White && !c.Black) return;
      var tr = el("tr");
      var first = el("td");
      var badge = el("span", "class-badge " + label.toLowerCase(), classificationMark(label));
      badge.title = label;
      first.appendChild(badge); first.appendChild(el("span", "class-name", label));
      tr.appendChild(first); tr.appendChild(el("td", "n", String(c.White))); tr.appendChild(el("td", "n", String(c.Black)));
      tr.tabIndex = 0; tr.setAttribute("role", "button"); tr.setAttribute("aria-label", "Jump to " + label + " move");
      function jump(){ var found=MOVES.findIndex(function(m){return (m.label||"Unclassified")===label;}); if(found>=0) select(found+1,true); }
      tr.addEventListener("click", jump); tr.addEventListener("keydown", function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();jump();}});
      body.appendChild(tr);
    });
    table.appendChild(body); host.appendChild(table);
  }

  function applyFilters() {
    /* No classification filter UI: keep the move sheet clean and show every move. */
    var cells = document.querySelectorAll(".move-cell[data-ply]");
    cells.forEach(function (cell) { cell.classList.toggle("hidden", false); });
  }
  function select(ply, scroll) {
    state.ply = Math.max(0, Math.min(MOVES.length, ply));
    document.querySelectorAll(".move-cell[data-ply]").forEach(function (cell) {
      var on = +cell.getAttribute("data-ply") === state.ply;
      cell.classList.toggle("sel", on);
      if (on) { cell.setAttribute("aria-current", "true"); /* Keep the viewport anchored on mobile; never scroll the whole page on move navigation. */ }
      else { cell.removeAttribute("aria-current"); }
    });
    var cursor = $("graph-cursor");
    if (cursor) {
      if (state.ply === 0) { cursor.style.display = "none"; }
      else {
        var x = DATA.graph.x0 + (DATA.graph.x1 - DATA.graph.x0) * state.ply / Math.max(1, MOVES.length);
        cursor.setAttribute("x1", x); cursor.setAttribute("x2", x); cursor.style.display = "block";
      }
    }
    state.candidateUci = null;
    renderBoard(); renderDetails(); renderCandidates();
    var nav = $("nav-position"); if (nav) { nav.textContent = state.ply ? (MOVES[state.ply-1].label_text + " " + MOVES[state.ply-1].san) : "Start"; }
  }
  function renderCandidates() {
    var host = $("candidate-list"); if (!host) return;
    host.textContent = "";
    var move = state.ply ? MOVES[state.ply - 1] : null;
    var list = move && move.candidate_moves ? move.candidate_moves.slice(0,3) : [];
    if (!list.length) { host.appendChild(el("span", "empty", "No candidate lines available for this position.")); return; }
    list.forEach(function(c, i) {
      var b = el("button", "candidate-btn"); b.type = "button"; b.setAttribute("aria-pressed", "false");
      b.appendChild(el("strong", null, (i+1) + ". " + c.san));
      b.appendChild(el("small", null, c.score || "Engine"));
      b.title = "Show candidate " + c.san + " on the board";
      b.addEventListener("click", function() {
        state.candidateUci = c.uci;
        host.querySelectorAll("button").forEach(function(x){x.setAttribute("aria-pressed", x===b ? "true":"false");});
        state.mode = "before"; setPressed("btn-mode", true); $("btn-mode").textContent = "Before";
        renderBoard();
      });
      host.appendChild(b);
    });
  }
  function setPressed(id, on) { var b = $(id); if (b) { b.setAttribute("aria-pressed", on ? "true" : "false"); } }

  function bind() {
    var viewSelect = $("details-view"); if (viewSelect) viewSelect.addEventListener("change", renderDetails);
    document.querySelectorAll(".move-cell[data-ply]").forEach(function (cell) {
      cell.addEventListener("click", function () { select(+cell.getAttribute("data-ply"), false); });
      cell.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(+cell.getAttribute("data-ply"), false); }
      });
    });
    document.querySelectorAll(".pt").forEach(function (pt) {
      pt.addEventListener("click", function () { select(+pt.getAttribute("data-ply"), true); });
    });
    var graph = $("graph");
    if (graph) {
      graph.addEventListener("click", function (e) {
        var box = graph.getBoundingClientRect(), vb = graph.viewBox.baseVal;
        var x = (e.clientX - box.left) / box.width * vb.width;
        var f = (x - DATA.graph.x0) / (DATA.graph.x1 - DATA.graph.x0);
        select(Math.round(f * MOVES.length), true);
      });
    }
    $("btn-first").addEventListener("click", function () { select(0, true); });
    $("btn-prev").addEventListener("click", function () { select(state.ply - 1, true); });
    $("btn-next").addEventListener("click", function () { select(state.ply + 1, true); });
    $("btn-last").addEventListener("click", function () { select(MOVES.length, true); });
    $("btn-flip").addEventListener("click", function () {
      state.flipped = !state.flipped; setPressed("btn-flip", state.flipped); renderBoard();
    });
    $("btn-mode").addEventListener("click", function () {
      state.mode = state.mode === "after" ? "before" : "after";
      state.candidateUci = null;
      setPressed("btn-mode", state.mode === "before");
      $("btn-mode").textContent = state.mode === "before" ? "Before" : "After";
      renderBoard(); renderCandidates();
    });
    document.addEventListener("keydown", function (e) {
      var tag = (e.target && e.target.tagName) || "";
      if (tag === "SELECT" || tag === "INPUT") { return; }
      if (e.key === "ArrowRight") { e.preventDefault(); select(state.ply + 1, true); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); select(state.ply - 1, true); }
      else if (e.key === "Home") { e.preventDefault(); select(0, true); }
      else if (e.key === "End") { e.preventDefault(); select(MOVES.length, true); }
      else if (e.key === "f" || e.key === "F") { $("btn-flip").click(); }
    });
  }

  try {
    var ready = $("board-fallback"); if (ready) { ready.style.display = "none"; }
    $("board-area").style.display = "block";
    bind(); applyFilters(); select(0, false);
    document.documentElement.setAttribute("data-plyra", "ready");
  } catch (err) {
    var fb = $("board-fallback");
    if (fb) { fb.style.display = "block"; fb.textContent = "The interactive board could not start (" + err.message + "). The move list and graph below still work."; }
    document.documentElement.setAttribute("data-plyra", "error");
  }
})();
"""
