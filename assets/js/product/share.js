function productShareUrl(productUrl) {
  const variantId = new URLSearchParams(window.location.search).get("pid");
  const url = new URL(productUrl, window.location.href);
  if (!variantId || url.pathname !== window.location.pathname) return productUrl;

  url.searchParams.set("pid", variantId);
  return url.href;
}

document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-product-share] a");
  if (!link) return;

  const productUrl = link.closest("[data-product-share]").dataset.productShare;
  if (!link.dataset.shareHref) link.dataset.shareHref = link.getAttribute("href");
  link.href = link.dataset.shareHref.replace(productUrl, encodeURIComponent(productShareUrl(productUrl)));
});

window.productShareUrl = productShareUrl;
