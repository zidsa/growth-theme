/**
 * JS mirror of the platform's image_url() Jinja macro (vitrin templates/macros.jinja).
 * Keep URLs identical to the server-rendered ones so the browser reuses them
 * instead of downloading another copy of the same image.
 *
 * No CDN host is hardcoded here:
 * - A source already served by a rendition service keeps that service
 *   (media.zid.store, img.zid.store, imgtest.zid.store, ...), like the macro does.
 * - A plain source uses the platform's default service, rendered by the server
 *   into [data-image-cdn] (see components/products/product-gallery.jinja).
 */

// "<origin>/<path segments>/<options with '='>/<source>", e.g.
// https://media.zid.store/cdn-cgi/image/w=750,q=90/https://media.zid.store/a.jpg
const RENDITION_RE = /^(https?:\/\/[^/]+\/(?:[^/=]+\/)*)([^/]*=[^/]*)\/(.+)$/;
const MAX_LAYERS = 10;

function defaultImageCdn() {
  return document.querySelector("[data-image-cdn]")?.dataset.imageCdn || "";
}

export function imageUrl(path, { w, h, q, f } = {}) {
  let src = String(path || "").trim();
  if (!src) return "";

  const params = [];
  if (w) params.push(`w=${w}`);
  if (h) params.push(`h=${h}`);
  if (q) params.push(`q=${q}`);
  if (f) params.push(`f=${f}`);

  // Peel off every rendition layer and remember the outermost one
  let outerPrefix = "";
  let outerOpts = "";
  for (let i = 0; i < MAX_LAYERS; i++) {
    const match = src.match(RENDITION_RE);
    if (!match) break;
    if (!outerPrefix) [, outerPrefix, outerOpts] = match;
    src = match[3];
  }

  if (params.length) {
    const cdn = outerPrefix || defaultImageCdn();
    // No known service to resize with: the original is better than a broken URL
    return cdn ? `${cdn}${params.join(",")}/${src}` : src;
  }
  if (outerOpts) return `${outerPrefix}${outerOpts}/${src}`;
  return src;
}

export function escapeAttr(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
