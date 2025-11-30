# Frontend Localization & Performance

## Performance Optimizations (Feature 008)

### Bundle Analysis
We use `rollup-plugin-visualizer` to analyze bundle sizes.
To generate a report:
```bash
cd frontend
export ANALYZE=true
npm run build
```
Report: `.internal/frontend-logs/perf/profiling/bundle-report.html`

### Optimizations Applied
1. **Textures**: Local WebP textures used in `ZenScene`.
2. **Code Splitting**: `lucide-react`, `framer-motion`, `three` are split into separate chunks.
3. **Defer Loading**: 3D scene is deferred by 2.5s.

### Metrics
- **TTI**: Target < 2s.
- **Bundle Size**: `vendor-react` < 700kB (currently ~660kB).
