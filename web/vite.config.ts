import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento (npm run dev) as chamadas /api vão para o servidor Python (radar web --nao-abrir).
// O build vai direto para dentro do pacote Python, que serve a interface em http://127.0.0.1:8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    outDir: "../src/radar/web_dist",
    emptyOutDir: true,
  },
});
