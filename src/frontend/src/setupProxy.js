const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Proxy /foundation to the backend for redirect
  app.use(
    '/foundation',
    createProxyMiddleware({
      target: 'http://backend:8000',
      changeOrigin: false,  // Keep original host header
      xfwd: true,           // Add X-Forwarded-* headers
    })
  );

  // Proxy all /api requests to backend
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://backend:8000',
      changeOrigin: true,
    })
  );
};
