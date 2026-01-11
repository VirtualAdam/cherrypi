FROM nginx:alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static HTML file (index.html if exists, otherwise example)
COPY index*.html /usr/share/nginx/html/

# Use index.html if it exists, otherwise rename example to index.html
RUN if [ -f /usr/share/nginx/html/index.html ]; then \
      rm -f /usr/share/nginx/html/index.example.html; \
    else \
      mv /usr/share/nginx/html/index.example.html /usr/share/nginx/html/index.html; \
    fi

EXPOSE 80
