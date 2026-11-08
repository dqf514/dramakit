(() => {
  "use strict";

  const main = document.getElementById("main");
  const rail = document.getElementById("rail");
  const side = document.getElementById("side");
  const jobNames = {
    run_pipeline: "制作流水线", health: "环境自检", setup: "智能配置",
    reindex: "资产索引", regen_shot: "镜头重新生成", character_refs: "角色参考图",
    duplicate_project: "复制项目", nodes_sync: "同步渲染模型",
    run_pipeline_action: "智能制作任务", regenerate_shot: "镜头重新生成"
  };
  const jobStatus = {
    queued: ["等待中", "run"], running: ["进行中", "run"], done: ["已完成", "done"],
    error: ["失败", "fail"], interrupted: ["已中断", "fail"], cancelled: ["已取消", ""]
  };
  let jobsLoading = false;
  let jobsRows = [];
  let jobFilters = {project: "", status: ""};
  let jobsShell = false;
  let lastDrawerFocus = null;

  // The task list is a tab of the workbench now. The console has three
  // places to be - workbench, nodes, settings - and everything else is a
  // tab inside one of them.
  const jobsPage = document.getElementById("page-jobs");

  const aiToggle = document.createElement("button");
  aiToggle.className = "btn sm ghost";
  aiToggle.id = "aiToggle";
  aiToggle.textContent = "AI 指令";
  aiToggle.title = "打开自然语言指令（Ctrl/⌘ K）";
  document.getElementById("themeBtn").before(aiToggle);

  function updateNav(name) {
    document.querySelectorAll(".railbtn[data-page]").forEach(btn => {
      const active = btn.dataset.page === name;
      btn.classList.toggle("on", active);
      if (active) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
  }

  const sideToggle = document.getElementById("sideToggle");

  function updateSideToggle() {
    const collapsed = side.classList.contains("hide");
    sideToggle.innerHTML = collapsed
      ? '<span aria-hidden="true">›</span><span>展开项目栏</span>'
      : '<span aria-hidden="true">‹</span><span>收起项目栏</span>';
    sideToggle.title = collapsed ? "展开项目栏" : "收起项目栏";
    sideToggle.setAttribute("aria-label", sideToggle.title);
    sideToggle.setAttribute("aria-expanded", String(!collapsed));
  }

  sideToggle.onclick = () => {
    side.classList.toggle("hide");
    updateSideToggle();
  };
  updateSideToggle();
  document.getElementById("brandBtn").onclick = () => switchPage("workbench");
  aiToggle.onclick = () => {
    const bar = document.getElementById("cmdbar");
    bar.classList.toggle("open");
    if (bar.classList.contains("open")) document.getElementById("cmd").focus();
  };

  function fmtBytes(value) {
    const n = Number(value || 0);
    if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)} GB`;
    if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(1)} MB`;
    return `${Math.max(0, Math.round(n / 1024))} KB`;
  }

  function fmtJobTime(job) {
    const start = job.started_at || job.created_at;
    const end = job.finished_at || Date.now() / 1000;
    const elapsed = Math.max(0, Math.round(end - start));
    return `${whenStr(job.created_at)} · ${elapsed >= 60 ? `${Math.floor(elapsed / 60)}分` : ""}${elapsed % 60}秒`;
  }

  function displayJobStatus(job) {
    const results = job.result?.results || job.result || {};
    if (job.status === "done" &&
        Object.values(results).some(v => v && typeof v === "object" && v.error)) {
      return ["部分失败", "fail"];
    }
    return jobStatus[job.status] || [job.status || "未知", ""];
  }

  async function loadJobs() {
    if (jobsLoading) return;
    jobsLoading = true;
    // Whether the list is on screen. It is asked for before the try:
    // the catch below reads it too, and a name declared inside the try
    // is not there when the call fails.
    const onJobs = S.activePage === "workbench" && S.wbTab === "jobs";
    try {
      const project = document.getElementById("jobProject")?.value || jobFilters.project;
      const status = document.getElementById("jobStatus")?.value || jobFilters.status;
      jobFilters = {project, status};
      // Off the jobs page only the badge needs updating: asking for 150
      // stored jobs every few seconds, on every page, is work nobody asked for.
      const params = new URLSearchParams({limit: onJobs ? "150" : "20"});
      if (onJobs && project) params.set("project", project);
      if (onJobs && status) params.set("status", status);
      const response = await getJSON(`/api/jobs?${params}`);
      jobsRows = response.jobs || [];
      const count = document.getElementById("jobCount");
      count.hidden = !response.active;
      count.textContent = response.active || "0";
      // The badge says how many, so it has to say it in words too.
      count.setAttribute("aria-label", response.active ? `${response.active} 个任务进行中` : "");
      if (onJobs) renderJobs();
    } catch (error) {
      if (onJobs) toast(`任务列表加载失败：${esc(error.message)}`, "err");
    } finally {
      jobsLoading = false;
    }
  }

  function renderJobs() {
    if (S.activePage !== "workbench" || S.wbTab !== "jobs") return;
    // The counts are about the work, not about the checks: a hundred
    // and forty-four finished checks are not a hundred and forty-four
    // things that were made.
    const work = jobsRows.filter(j => j.kind !== "health");
    const active = work.filter(j => ["queued", "running"].includes(j.status)).length;
    const stalled = work.filter(j => {
      const label = displayJobStatus(j)[0];
      // "needs attention" means anything that did not finish cleanly:
      // a failure, a half-done result, a stop, or a run a restart left behind.
      return label === "失败" || label === "部分失败" || label === "已中断" || label === "已取消";
    }).length;
    const done = work.filter(j => j.status === "done").length;
    if (!jobsShell) {
      // The frame is drawn once. Redrawing it on every poll closed the
      // log panel the user had just opened and dropped the scroll
      // position every three seconds.
      jobsPage.innerHTML = `
        <h1 class="page">任务</h1>
        <div class="job-overview" id="jobStats"></div>
        <div class="job-filters">
          <div class="grow"><label class="fl" for="jobProject">项目</label><select class="f" id="jobProject"><option value="">全部项目</option>${S.projects.map(p => `<option value="${attr(p.slug)}">${esc(p.title)}</option>`).join("")}</select></div>
          <div><label class="fl" for="jobStatus">状态</label><select class="f" id="jobStatus"><option value="">全部状态</option><option value="running">进行中</option><option value="queued">等待中</option><option value="done">已完成</option><option value="error">失败</option><option value="interrupted">已中断</option></select></div>
          <button class="btn ghost" id="jobRefresh">刷新</button>
        </div>
        <div class="job-list" id="jobList"></div>
        <details class="fold" style="margin-top:16px"><summary>查看最近系统日志</summary><div class="inner"><div class="log-panel" id="jobLogs">展开时读取</div></div></details>`;
      jobsShell = true;
      document.getElementById("jobProject").onchange = loadJobs;
      document.getElementById("jobStatus").onchange = loadJobs;
      document.getElementById("jobRefresh").onclick = loadJobs;
      const logDetails = jobsPage.querySelector("details");
      logDetails.addEventListener("toggle", async () => {
        if (!logDetails.open) return;
        const r = await getJSON("/api/logs?n=160");
        const box = document.getElementById("jobLogs");
        if (box) box.textContent = (r.lines || []).map(x => `${whenStr(x.t)}  ${x.msg}`).join("\n") || "暂无日志";
      });
    }
    const projectBox = document.getElementById("jobProject");
    // A project created after the frame was built still has to appear in
    // the filter, so the options are rebuilt each time; the chosen one is
    // put back after.
    projectBox.innerHTML = `<option value="">全部项目</option>${S.projects.map(p => `<option value="${attr(p.slug)}">${esc(p.title)}</option>`).join("")}`;
    projectBox.value = jobFilters.project;
    document.getElementById("jobStatus").value = jobFilters.status;
    document.getElementById("jobStats").innerHTML = `
      <div class="job-stat"><b>${active}</b><span>等待或运行中</span></div>
      <div class="job-stat"><b>${done}</b><span>已完成</span></div>
      <div class="job-stat"><b>${stalled}</b><span>需要处理</span></div>
      <div class="job-stat"><b>${work.length}</b><span>最近任务</span></div>`;
    const list = document.getElementById("jobList");
    // What is running comes first: the person came here to see it.
    const running = jobsRows.filter(j => ["queued", "running"].includes(j.status));
    const checks = jobsRows.filter(j => j.kind === "health");
    const rest = jobsRows.filter(j => !["queued", "running"].includes(j.status)
      && j.kind !== "health");
    const byTime = (a, b) => (b.created_at || 0) - (a.created_at || 0);
    const main = [...running.sort(byTime), ...rest.sort(byTime)];
    list.innerHTML = main.length ? main.map(jobRow).join("")
      : '<div class="empty">还没有任务记录<button class="btn confirm empty-action" id="jobToStudio">去制作</button></div>';
    // The environment check runs every few minutes and fills the list
    // with rows that say nothing; it keeps its own place at the bottom.
    if (checks.length) {
      const box = document.createElement("details");
      box.className = "fold";
      box.style.marginTop = "12px";
      box.innerHTML = `<summary>环境自检（${checks.length} 条）</summary>`
        + `<div class="inner">${checks.map(jobRow).join("")}</div>`;
      list.appendChild(box);
    }
    document.getElementById("jobToStudio")?.addEventListener("click", () => {
      switchPage("workbench"); S.wbTab = "flow"; showWbTab("flow");
    });
    list.querySelectorAll("[data-job-stop]").forEach(btn => btn.onclick = async () => {
      btn.disabled = true;
      const r = await postJSON("/api/jobs/stop", {job: btn.dataset.jobStop});
      toast(r.ok ? "已请求停止，当前调用结束后会保留已完成内容" : (r.error || "无法停止"), r.ok ? "ok" : "err");
      await loadJobs();
    });
    list.querySelectorAll("[data-job-resume]").forEach(btn => btn.onclick = async () => {
      btn.disabled = true;
      const r = await postJSON("/api/resume", {project: btn.dataset.jobResume});
      if (!r || !r.ok) {
        toast((r && r.error) || "没有可续跑的记录", "err", 4200);
        btn.disabled = false;
        return;
      }
      toast("已按上次的计划继续", "ok");
      await loadJobs();
    });
    list.querySelectorAll("[data-job-project]").forEach(btn => btn.onclick = async () => {
      await selectProject(btn.dataset.jobProject, true);
      switchPage("workbench");
    });
  }

  function jobRow(job) {
    const [label, cls] = displayJobStatus(job);
    const project = S.projects.find(p => p.slug === job.project);
    const progress = job.progress || {};
    const known = progress.total ? Math.min(100, Math.round((progress.done || 0) * 100 / progress.total)) : (progress.percent || 0);
    const active = ["queued", "running"].includes(job.status);
    // A run that stopped can be carried on from where it stopped: the
    // plan is on the project, and the stages that are done are skipped.
    const resumable = job.kind === "run_pipeline" && !active && !!job.project
      && ["interrupted", "error", "cancelled"].includes(job.status);
    // A running job that has not reported a count gets the crawl bar,
    // not an invented percentage: the console cannot know how far along
    // it is, and a made-up number reads as a measurement.
    const bar = known ? `<div class="job-progress"><i style="width:${known}%"></i></div>`
      : (active && job.status === "running" ? '<div class="job-progress indet"><i></i></div>' : "");
    return `<article class="job-row ${active ? "active" : ""}">
      <div><div class="job-title">${esc(jobNames[job.kind] || job.kind)}</div><div class="job-sub">#${esc(job.id)} · ${esc(job.kind)}</div></div>
      <div class="job-project">${project ? `<button class="btn xs ghost" data-job-project="${attr(job.project)}">${esc(project.title)}</button>` : '<span class="muted">系统任务</span>'}</div>
      <div><span class="badge ${cls}">${esc(label)}</span></div>
      <div class="job-progress-wrap"><div class="job-time">${fmtJobTime(job)}</div>${bar}</div>
      <div class="job-actions">${active ? `<button class="btn xs danger" data-job-stop="${attr(job.id)}">停止</button>` : ""}${resumable ? `<button class="btn xs ghost" data-job-resume="${attr(job.project)}" title="按这个任务当时的计划继续（已完成的步骤会跳过）">↻ 续跑</button>` : ""}${job.kind === "run_pipeline" && !active && job.project ? `<button class="btn xs ghost" data-job-project="${attr(job.project)}">打开项目</button>` : ""}</div>
      ${job.error ? `<div class="job-error">${esc(job.error)}</div>` : ""}
    </article>`;
  }

  window.runPreflight = function(stages, label, body = {}) {
    if (!S.current && !body.project) {
      toast("请先新建或选择一个项目", "err");
      return Promise.resolve(false);
    }
    return new Promise(resolve => {
      const dialog = document.createElement("dialog");
      dialog.className = "dk-dialog";
      dialog.setAttribute("aria-modal", "true");
      dialog.setAttribute("aria-labelledby", "preflightTitle");
      const before = document.activeElement;
      const project = S.projects.find(p => p.slug === (body.project || S.current));
      const episodes = body.episodes?.length ? body.episodes.join("、") : "全部集数";
      const chapters = body.chapters?.length ? body.chapters.join("、") : "按项目当前选择";
      const config = S.state?.config_summary || {};
      // The frame and the look decide every picture and every clip, so
      // they are in the dialog: the run has to be the one that was
      // confirmed, and it has to be visible.
      const ad = (S.detail && S.detail.art_direction) || {};
      const draft = (S.lookDraft && S.lookDraft.project === (body.project || S.current))
        ? S.lookDraft : null;
      const ratio = (draft && draft.aspect_ratio) || ad.aspect_ratio || "";
      const fw = (draft && draft.width) || ad.frame_width
        || (S.detail && S.detail.frame && S.detail.frame.width) || 0;
      const fh = (draft && draft.height) || ad.frame_height
        || (S.detail && S.detail.frame && S.detail.frame.height) || 0;
      const sid = (draft && draft.style) || "";
      const srow = ((LOOKS && LOOKS.styles) || []).find(s => s.id === sid);
      const frameTxt = [ratio, (fw && fh) ? (fw + "\u00d7" + fh) : ""]
        .filter(Boolean).join(" \u00b7 ") || "未设置";
      const styleTxt = srow ? srow.name : (ad.style || sid || "未设置");
      dialog.innerHTML = `<div class="dialog-head"><h2 id="preflightTitle">确认执行${esc(label || "制作任务")}</h2><div class="muted">检查范围与外部服务后再开始，避免重复生成和意外覆盖。</div></div>
        <div class="dialog-body"><dl class="preflight-grid">
          <dt>项目</dt><dd>${esc(project?.title || body.project || S.current)}</dd>
          <dt>画幅 / 分辨率</dt><dd>${esc(frameTxt)}</dd>
          <dt>风格</dt><dd>${esc(styleTxt)}</dd>
          <dt>处理范围</dt><dd>${esc(episodes)} · ${esc(chapters)}</dd>
          <dt>执行阶段</dt><dd>${stages.map(s => esc(STAGE_ZH[s] || s)).join(" → ")}</dd>
          <dt>文本模型</dt><dd>${esc(config.default_model || "未配置")}</dd>
          <dt>画面服务</dt><dd>${esc(config.comfyui || "未配置")}${config.comfyui_enabled ? "" : "（已禁用）"}</dd>
          <dt>配音服务</dt><dd>${esc(config.tts || "未配置")}</dd>
        </dl><div class="preflight-note">共 ${stages.length} 个阶段。已完成内容默认跳过；重跑和返工可能更新现有资产。生成耗时与费用取决于集数、镜头数和 Provider 用量，请在运行前确认额度。</div></div>
        <div class="dialog-foot"><button class="btn ghost" data-cancel>返回检查</button><button class="btn go" data-confirm>开始运行</button></div>`;
      document.body.appendChild(dialog);
      const finish = value => {
        if (dialog.open) dialog.close();
        dialog.remove();
        // the caret goes back where the button that opened this was
        before?.focus?.();
        resolve(value);
      };
      dialog.querySelector("[data-cancel]").onclick = () => finish(false);
      dialog.querySelector("[data-confirm]").onclick = () => finish(true);
      dialog.addEventListener("cancel", event => { event.preventDefault(); finish(false); });
      dialog.showModal();
      /* focus the way out, not the way in: this dialog precedes a run
        that can spend money and overwrite assets, and a stray Enter
        should not start it */
      dialog.querySelector("[data-cancel]").focus();
    });
  };

  async function renderConfigHistory() {
    const shell = document.getElementById("page-settings-hist");
    if (!shell) return;
    // The card lives beside the settings tab, not inside it: the tab is
    // rewritten from scratch on every visit, and a card living in it was
    // thrown away and rebuilt each time the page opened.
    let card = document.getElementById("configHistoryCard");
    if (!card) {
      card = document.createElement("div");
      card.className = "card";
      card.id = "configHistoryCard";
      shell.appendChild(card);
    }
    card.innerHTML = '<h3>配置版本 <span class="muted">读取中…</span></h3>';
    const r = await getJSON("/api/config/history");
    const versions = r.versions || [];
    card.innerHTML = `<h3>配置版本 <span class="muted">保留最近 30 个；回滚前自动备份当前配置</span></h3>${versions.length ? versions.slice(0, 10).map(v => `<div class="version-row"><div class="grow"><b>${whenStr(v.created_at)}</b><div class="muted">${fmtBytes(v.bytes)} · ${esc(v.id)}</div></div><button class="btn xs ghost" data-version="${attr(v.id)}">回滚到此版本</button></div>`).join("") : '<div class="empty">修改模型或制作参数后会自动形成版本</div>'}`;
    card.querySelectorAll("[data-version]").forEach(btn => btn.onclick = async () => {
      if (!confirm(`确定回滚到 ${whenStr((versions.find(v => v.id === btn.dataset.version) || {}).created_at)} 的配置吗？\n当前配置会先自动备份。`)) return;
      const result = await postJSON("/api/config/restore", {id: btn.dataset.version});
      if (!result.ok) return toast(`回滚失败：${esc(result.error)}`, "err");
      S.unsaved = false;
      toast("配置已回滚", "ok");
      await boot();
      await renderConfigHistory();
    });
  }

  async function renderTrash() {
    const box = document.getElementById("trashList");
    if (!box) return;
    box.innerHTML = '<div class="muted">读取中…</div>';
    const r = await getJSON("/api/projects/trash");
    const rows = r.projects || [];
    box.innerHTML = rows.length ? rows.map(p => `<div class="trash-row"><div class="grow"><b>${esc(p.name)}</b><div class="muted">${fmtBytes(p.bytes)} · ${ago(p.deleted_at)}移入</div></div><button class="btn xs confirm" data-restore="${attr(p.slug)}">恢复项目</button></div>`).join("") : '<div class="empty">回收站为空</div>';
    box.querySelectorAll("[data-restore]").forEach(btn => btn.onclick = async () => {
      const result = await postJSON("/api/projects/manage", {action: "restore", project: btn.dataset.restore});
      if (!result.ok) return toast(result.error, "err");
      toast("项目已恢复", "ok");
      await boot();
      await selectProject(result.project, true);
      switchPage("workbench");
    });
  }

  function enhanceWorkbench() {
    const box = document.getElementById("page-flow");
    // with no project there is nothing to rename, copy or restore
    if (!box || !S.current || document.getElementById("projectManagement")) return;
    const details = document.createElement("details");
    details.className = "fold";
    details.id = "projectManagement";
    details.innerHTML = `<summary>项目管理</summary><div class="inner">
      <div class="management-grid"><div><b>当前项目</b><div class="muted" id="projectStorage">可查看磁盘占用或创建完整副本</div><div class="management-actions"><button class="btn ghost" id="renameProject">重命名</button><button class="btn ghost" id="duplicateProject">复制项目</button><button class="btn ghost" id="projectStats">统计占用</button></div></div>
      <div><b>回收站</b><div class="muted">删除的项目可在这里恢复</div><div id="trashList"></div></div></div></div>`;
    // The management panel is about a project, so it lives in the column
    // of projects: the column is wide enough for it, and it does not push
    // the work down the page.
    const host = document.querySelector("#side .side-content")
      || box.querySelector(".wb-main") || box;
    host.appendChild(details);
    document.getElementById("renameProject").onclick = async () => {
      const current = S.detail?.meta?.title || S.current;
      const name = prompt("输入新的项目名称", current)?.trim();
      if (!name || name === current) return;
      const r = await postJSON("/api/projects/manage", {action: "rename", project: S.current, name});
      if (!r.ok) return toast(r.error, "err");
      S.current = "";
      await boot();
      await selectProject(r.project, true);
      toast("项目已重命名", "ok");
    };
    document.getElementById("duplicateProject").onclick = async () => {
      const name = prompt("副本名称", `${S.detail?.meta?.title || S.current} 副本`)?.trim();
      if (!name) return;
      const r = await postJSON("/api/projects/manage", {action: "duplicate", project: S.current, name});
      if (!r.ok) return toast(r.error, "err");
      toast("复制任务已提交，可在任务中心查看", "ok");
      pollJob(r.job, async result => {
        if (!result) return;
        await boot();
        await selectProject(result.project, true);
        switchPage("workbench");
      });
    };
    document.getElementById("projectStats").onclick = async () => {
      const r = await postJSON("/api/projects/manage", {action: "stats", project: S.current});
      if (r.ok) document.getElementById("projectStorage").textContent = `当前项目占用 ${fmtBytes(r.bytes)}`;
    };
    // Every time it opens, not the first: a project deleted since the
    // last visit would otherwise stay invisible until the page was rebuilt.
    details.addEventListener("toggle", () => { if (details.open) renderTrash(); });
  }

  function renderFilmStrip() {
    const box = document.getElementById("page-board");
    const d = S.detail;
    if (!d || !box.querySelector(".boardbar")) return;
    box.querySelector(".film-strip")?.remove();
    const ep = (d.episodes || []).find(e => e.index === S.boardEp) || (d.episodes || [])[0];
    if (!ep) return;
    const strip = document.createElement("div");
    strip.className = "film-strip";
    strip.setAttribute("aria-label", `第${ep.index}集场次带`);
    strip.innerHTML = ep.scenes.map(sc => `<button class="film-scene" data-scene="${attr(sc.id)}"><b>SC ${String(sc.index).padStart(2, "0")} · ${sc.shots.length} 镜</b><span>${esc(sc.location || "未命名场景")}</span><span>${esc(sc.time || "")}</span></button>`).join("");
    box.querySelector(".boardbar").after(strip);
    strip.querySelectorAll("[data-scene]").forEach(btn => btn.onclick = () => {
      const target = box.querySelector(`[data-sc="${CSS.escape(btn.dataset.scene)}"]`);
      if (!target) {
        // The board can be filtered down to one kind of scene, and then
        // there is nothing to jump to. Saying so beats scrolling nowhere.
        toast("这个场次被当前筛选挡住了，先清除筛选", "", 2400);
        return;
      }
      target.scrollIntoView({behavior: "smooth", block: "start"});
    });
  }

  let fieldSeq = 0;
  function enhanceA11y(root = document) {
    // Each node is tagged once. Without the tag the observer re-walked
    // every card in the page on every DOM change, regenerating field ids
    // that already had one. Only the things that are not already controls
    // get a role: a native button does not need to be told it is one.
    const nodes = root.querySelectorAll('.chip:not(button),.tg:not(button),.proj,.stg,.pcard,.shotcard,.epcard,.anode,.mini[onclick]');
    nodes.forEach(node => {
      if (node.dataset.dkA11y) return;
      node.dataset.dkA11y = "1";
      if (!node.getAttribute("role")) node.setAttribute("role", "button");
      if (!node.hasAttribute("tabindex")) node.tabIndex = 0;
    });
    root.querySelectorAll("svg:not([aria-hidden])").forEach(svg => {
      if (!svg.getAttribute("aria-label")) svg.setAttribute("aria-hidden", "true");
    });
    root.querySelectorAll("input.f,select.f,textarea.f").forEach(field => {
      if (field.getAttribute("aria-label") || field.getAttribute("aria-labelledby")) return;
      const label = field.closest("div")?.querySelector(":scope > label.fl") || field.previousElementSibling;
      if (label?.tagName !== "LABEL") return;
      if (!field.id) {
        fieldSeq += 1;
        field.id = `dk-field-${fieldSeq}`;
      }
      label.htmlFor = field.id;
    });
  }

  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      document.getElementById("cmdbar").classList.add("open");
      document.getElementById("cmd").focus();
    }
    if (event.key === "Escape") {
      if (document.getElementById("drawer").classList.contains("show")) closeDrawer();
    }
    if ((event.key === "Enter" || event.key === " ") && event.target.matches('[role="button"]')) {
      event.preventDefault();
      event.target.click();
    }
  });
  document.addEventListener("input", event => {
    if (event.target.closest("#page-settings")) {
      S.unsaved = true;
      let bar = document.getElementById("unsavedBar");
      if (!bar) {
        bar = document.createElement("div");
        bar.id = "unsavedBar";
        bar.className = "unsaved-bar";
        bar.innerHTML = '<b>有未保存的更改</b><span class="muted">保存后才会影响后续任务；正在运行的任务不受影响。</span>';
        document.getElementById("page-settings").appendChild(bar);
      }
    }
  });
  window.addEventListener("beforeunload", event => {
    if (S.unsaved) { event.preventDefault(); event.returnValue = ""; }
  });

  const originalSwitchPage = switchPage;
  switchPage = function(name, force) {
    if (S.activePage === "settings" && name !== "settings" && S.unsaved &&
        !confirm("设置尚未保存。确定离开并放弃未保存的修改吗？")) return;
    if (name !== "settings") S.unsaved = false;
    const result = originalSwitchPage(name, force);
    updateNav(name);
    enhanceA11y(main);
    return result;
  };

  const originalRenderWorkbench = renderWorkbench;
  renderWorkbench = function() {
    const result = originalRenderWorkbench();
    enhanceA11y(document.getElementById("page-workbench"));
    return result;
  };

  const originalRenderFlow = renderFlow;
  renderFlow = function() {
    const result = originalRenderFlow();
    enhanceWorkbench();
    enhanceA11y(document.getElementById("page-flow"));
    return result;
  };

  const originalRenderBoard = renderBoard;
  renderBoard = function() {
    const result = originalRenderBoard();
    renderFilmStrip();
    enhanceA11y(document.getElementById("page-board"));
    return result;
  };

  const originalLoadSettings = loadSettings;
  loadSettings = async function() {
    const result = await originalLoadSettings();
    S.unsaved = false;
    document.getElementById("unsavedBar")?.remove();
    enhanceA11y(document.getElementById("page-settings"));
    return result;
  };

  const originalStartStages = startStages;
  startStages = async function(stages, label) {
    if (!(await runPreflight(stages, label, {project: S.current, episodes: []}))) return;
    return originalStartStages(stages, label);
  };

  ["saveModels", "saveAI", "saveProduction"].forEach(name => {
    const original = window[name];
    if (typeof original !== "function") return;
    window[name] = async function(...args) {
      const result = await original(...args);
      S.unsaved = false;
      document.getElementById("unsavedBar")?.remove();
      return result;
    };
  });

  const originalShowDrawer = showDrawer;
  showDrawer = function() {
    lastDrawerFocus = document.activeElement;
    const drawer = document.getElementById("drawer");
    drawer.setAttribute("role", "dialog");
    drawer.setAttribute("aria-modal", "true");
    drawer.setAttribute("aria-label", document.getElementById("dTitle").textContent || "编辑");
    const result = originalShowDrawer();
    setTimeout(() => drawer.querySelector("input,textarea,select,button")?.focus(), 0);
    return result;
  };
  const originalCloseDrawer = closeDrawer;
  closeDrawer = function() {
    const result = originalCloseDrawer();
    lastDrawerFocus?.focus?.();
    return result;
  };

  window.renderJobs = renderJobs;
  window.loadJobs = loadJobs;
  window.renderConfigHistory = renderConfigHistory;

  document.getElementById("toast").setAttribute("role", "status");
  document.getElementById("toast").setAttribute("aria-live", "polite");
  new MutationObserver(() => enhanceA11y(main)).observe(main, {childList: true, subtree: true});
  enhanceA11y();
  updateNav(S.activePage || "workbench");
  setInterval(() => {
    if (!document.hidden) loadJobs();
  }, 3000);
})();
