function parseTsvRows(text) {
  const rows = [[]];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (inQuotes) {
      if (char === '"' && next === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        cell += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === "\t") {
      rows.at(-1).push(cell);
      cell = "";
    } else if (char === "\r" || char === "\n") {
      rows.at(-1).push(cell);
      cell = "";
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      rows.push([]);
    } else {
      cell += char;
    }
  }

  rows.at(-1).push(cell);
  return rows.filter((row) => row.some((value) => value.trim()));
}

function hasHeader(row) {
  return row[0]?.trim() === "소파트"
    && row[1]?.trim() === "대업무"
    && row[2]?.trim() === "세부업무";
}

function decodeHtmlText(value) {
  return String(value ?? "")
    .replaceAll("&nbsp;", " ")
    .replaceAll("&#160;", " ")
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", "\"")
    .replaceAll("&#39;", "'")
    .replaceAll("&#039;", "'");
}

function htmlCellToText(value) {
  return decodeHtmlText(
    String(value ?? "")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<[^>]+>/g, "")
      .replace(/\u00a0/g, " "),
  ).trim();
}

function parseHtmlTableRows(html) {
  if (!html || !String(html).match(/<table[\s>]/i)) {
    return [];
  }

  if (typeof DOMParser !== "undefined") {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const table = doc.querySelector("table");
    if (table) {
      return [...table.querySelectorAll("tr")]
        .map((row) => [...row.querySelectorAll("th,td")]
          .map((cell) => (cell.textContent || "").replace(/\u00a0/g, " ").trim()))
        .filter((row) => row.some((value) => value.trim()));
    }
  }

  const tableHtml = String(html).match(/<table[\s\S]*?<\/table>/i)?.[0] || "";
  const rowMatches = tableHtml.match(/<tr[\s\S]*?<\/tr>/gi) || [];
  return rowMatches
    .map((rowHtml) => (rowHtml.match(/<t[dh][^>]*>[\s\S]*?<\/t[dh]>/gi) || [])
      .map((cellHtml) => htmlCellToText(cellHtml)))
    .filter((row) => row.some((value) => value.trim()));
}

function rowsToTasks(rows, options = {}) {
  if (rows.length && hasHeader(rows[0])) {
    rows.shift();
  }

  const organizationId = options.organizationId ?? 1;

  return rows.map((row) => {
    let cursor = 0;
    const subPart = row[cursor++]?.trim() || "";
    const majorTask = row[cursor++]?.trim() || "";
    const detailTask = row[cursor++]?.trim() || "";

    return {
      organization_id: organizationId,
      sub_part: subPart,
      major_task: majorTask,
      detail_task: detailTask,
      confidential_answers: [],
      conf_data_type: "",
      conf_owner_user: "",
      national_tech_answers: [],
      ntech_data_type: "",
      ntech_owner_user: "",
      is_compliance: false,
      comp_data_type: "",
      comp_owner_user: "",
      storage_location: "",
      related_menu: "",
      share_scope: "",
    };
  });
}

export function parseTsvToTasks(text, questions = {}, options = {}) {
  return rowsToTasks(parseTsvRows(text), options);
}

export function parseClipboardToTasks(payload, questions = {}, options = {}) {
  const clipboard = typeof payload === "string" ? { text: payload, html: "" } : (payload || {});
  const htmlRows = parseHtmlTableRows(clipboard.html || "");
  if (htmlRows.length) {
    return rowsToTasks(htmlRows, options);
  }
  return parseTsvToTasks(clipboard.text || "", questions, options);
}
