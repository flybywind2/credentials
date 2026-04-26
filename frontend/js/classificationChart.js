function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeCount(value) {
  const numberValue = Number(value || 0);
  return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : 0;
}

function normalizedSummary(summary = {}) {
  const applicable = normalizeCount(summary.applicable);
  const explicitTotal = normalizeCount(summary.total);
  const explicitNotApplicable = normalizeCount(summary.not_applicable);
  const total = explicitTotal || applicable + explicitNotApplicable;
  const notApplicable = Math.max(total - applicable, 0);
  return {
    total,
    applicable: Math.min(applicable, total),
    not_applicable: notApplicable,
  };
}

export function classificationSummaryFromTasks(tasks = []) {
  const applicable = tasks.filter(
    (task) => task.is_confidential || task.is_national_tech || task.is_compliance,
  ).length;
  return {
    total: tasks.length,
    applicable,
    not_applicable: tasks.length - applicable,
  };
}

export function classificationDonutStyle(summary = {}) {
  const { total, applicable } = normalizedSummary(summary);
  if (!total) {
    return "background: #eee8f8";
  }
  const applicableDegrees = Math.round((applicable / total) * 360);
  return `background: conic-gradient(#8f6be8 0deg ${applicableDegrees}deg, #d9dce8 ${applicableDegrees}deg 360deg)`;
}

export function classificationPercent(value, total) {
  if (!total) {
    return 0;
  }
  return Math.round((value / total) * 100);
}

export function renderClassificationDonut(summary = {}, title = "해당/미해당 비율") {
  const normalized = normalizedSummary(summary);
  const applicableRate = classificationPercent(normalized.applicable, normalized.total);
  return `
    <section class="classification-donut-card" aria-label="${escapeHtml(title)}">
      <div class="classification-donut" style="${classificationDonutStyle(normalized)}">
        <div class="classification-donut-center">
          <strong>${applicableRate}%</strong>
          <span>해당</span>
        </div>
      </div>
      <div class="classification-donut-copy">
        <h3>${escapeHtml(title)}</h3>
        <div class="donut-legend">
          <span><i class="legend-dot classification-applicable"></i>해당 ${normalized.applicable}건</span>
          <span><i class="legend-dot classification-not-applicable"></i>미해당 ${normalized.not_applicable}건</span>
          <span>전체 ${normalized.total}건</span>
        </div>
      </div>
    </section>
  `;
}
