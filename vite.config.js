import { defineConfig } from "vite";
import { resolve } from "path";

// Build config - pass ENTRY env var to build specific bundle
const entry = process.env.ENTRY || "main";

const entries = {
  main: {
    entry: resolve(__dirname, "assets/js/main.js"),
    name: "VitrinTheme",
    fileName: "theme"
  },
  cart: {
    entry: resolve(__dirname, "assets/js/cart/controller.js"),
    name: "CartController",
    fileName: "cart-controller"
  }
};

const config = entries[entry] || entries.main;

export default defineConfig({
  build: {
    outDir: "assets/dist",
    emptyOutDir: entry === "main", // Only empty on main build
    sourcemap: process.env.NODE_ENV !== "production",
    minify: process.env.NODE_ENV === "production",

    // Library mode - outputs a single IIFE bundle for browser <script> tag
    lib: {
      entry: config.entry,
      name: config.name,
      formats: ["iife"],
      fileName: () => `${config.fileName}.js`
    }
  }
});
