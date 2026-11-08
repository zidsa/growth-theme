/**
 * JS mirror of the platform's image_url() Jinja macro (vitrin templates/macros.jinja).
 * Keep URLs identical to the server-rendered ones so the browser reuses them
 * instead of downloading another copy of the same image.
 */

const IMAGE_CDN = "https://media.zid.store/cdn-cgi/image/";

export function imageUrl(path, { w, h, q, f } = {}) {
  let src = String(path || "");
  if (!src) return "";

  const params = [];
  if (w) params.push(`w=${w}`);
  if (h) params.push(`h=${h}`);
  if (q) params.push(`q=${q}`);
  if (f) params.push(`f=${f}`);
  if (!params.length) return src;

  // Drop existing CDN options (e.g. fit=scale-down,width=370,...) and keep the original path
  if (src.startsWith(IMAGE_CDN)) {
    const rest = src.slice(IMAGE_CDN.length);
    src = rest.includes("/") ? rest.split("/").slice(1).join("/") : rest;
  }
  return `${IMAGE_CDN}${params.join(",")}/${src}`;
}

export function escapeAttr(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
