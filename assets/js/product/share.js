const VARIANT_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const serverHrefs = new WeakMap();

function decodedPath(href) {
  return decodeURIComponent(new URL(href, window.location.href).pathname).replace(/\/+$/, "");
}

function productShareUrl(productUrl) {
  const variantId = new URLSearchParams(window.location.search).get("pid");
  if (!VARIANT_ID_PATTERN.test(variantId)) return productUrl;
  if (!decodedPath(window.location.href).endsWith(decodedPath(productUrl))) return productUrl;

  const url = new URL(productUrl, window.location.href);
  url.searchParams.set("pid", variantId);
  return url.href;
}

function updateShareLink(event) {
  const link = event.target.closest("[data-product-share] a");
  if (!link) return;

  const productUrl = link.closest("[data-product-share]").dataset.productShare;
  if (!serverHrefs.has(link)) serverHrefs.set(link, link.getAttribute("href"));
  link.href = serverHrefs.get(link).replace(productUrl, encodeURIComponent(productShareUrl(productUrl)));
}

document.addEventListener("pointerdown", updateShareLink);
document.addEventListener("click", updateShareLink);

window.productShareUrl = productShareUrl;
