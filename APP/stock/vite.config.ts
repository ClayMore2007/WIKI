import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    noDiscovery: true,
    include: ["react", "react-dom", "react-dom/client"]
  },
  server: {
    host: "127.0.0.1",
    port: 5173
  }
});
