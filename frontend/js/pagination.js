export const PAGE_SIZE = 20;

export function pageCount(total, pageSize = PAGE_SIZE) {
  return Math.max(1, Math.ceil(Number(total || 0) / pageSize));
}

export function clampPage(page, total, pageSize = PAGE_SIZE) {
  const maxPage = pageCount(total, pageSize);
  return Math.min(Math.max(Number(page || 1), 1), maxPage);
}

export function paginateItems(items, page = 1, pageSize = PAGE_SIZE) {
  const safeItems = Array.isArray(items) ? items : [];
  const safePage = clampPage(page, safeItems.length, pageSize);
  const start = (safePage - 1) * pageSize;
  return {
    items: safeItems.slice(start, start + pageSize),
    page: safePage,
    pageSize,
    total: safeItems.length,
    totalPages: pageCount(safeItems.length, pageSize),
  };
}

export function paginationSummary({ total, page, pageSize = PAGE_SIZE }) {
  if (!total) {
    return "0 / 0";
  }
  const start = ((page - 1) * pageSize) + 1;
  const end = Math.min(page * pageSize, total);
  return `${start}-${end} / ${total}`;
}

export function renderPaginationControls(pagination, target) {
  return `
    <nav class="pagination-bar" aria-label="페이지 이동" data-pagination-target="${target}">
      <button type="button" class="secondary-button" data-page-action="prev" ${pagination.page <= 1 ? "disabled" : ""}>이전</button>
      <span>${paginationSummary(pagination)} · ${pagination.page} / ${pagination.totalPages}</span>
      <button type="button" class="secondary-button" data-page-action="next" ${pagination.page >= pagination.totalPages ? "disabled" : ""}>다음</button>
    </nav>
  `;
}
