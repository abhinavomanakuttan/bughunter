"""
BugHunter Demo — Intentionally Broken Web Application
Serves as a local target for testing BugHunter's bug detection capabilities.

Bugs intentionally included:
1. Broken image (404 src)
2. JavaScript error on load
3. Form that fails to submit
4. Broken navigation link (404)
5. Missing alt text on images (a11y)
6. Button with no accessible label (a11y)
7. HTTP 500 endpoint
8. CORS error endpoint
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

demo_app = FastAPI(title="BugHunter Demo Site (Intentionally Broken)")

_DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bug-Ridden Demo Store</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        nav a { color: white; margin-right: 15px; text-decoration: none; }
        .products { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
        .product-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .product-card img { width: 100%; height: 150px; object-fit: cover; }
        button { background: #e74c3c; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 4px; }
        button:hover { background: #c0392b; }
        form { background: white; padding: 20px; border-radius: 8px; margin-top: 20px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .error-section { background: #fee; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid #fcc; }
        footer { margin-top: 30px; text-align: center; color: #666; }
    </style>
</head>
<body>
    <header>
        <h1>Demo Store — Bug Hunt Edition</h1>
        <nav>
            <a href="/">Home</a>
            <a href="/products">Products</a>
            <!-- BUG: broken link -->
            <a href="/about-us-this-page-does-not-exist">About</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>

    <!-- BUG: JavaScript error on load -->
    <script>
        window.onload = function() {
            // This will throw a TypeError
            var obj = null;
            console.error('Demo site error: ' + obj.nonExistentProperty);
        };
    </script>

    <main>
        <h2>Featured Products</h2>
        <div class="products">
            <div class="product-card">
                <!-- BUG: Broken image (404) -->
                <img src="/static/images/product-nonexistent.jpg" alt="Widget Pro">
                <h3>Widget Pro</h3>
                <p>$29.99</p>
                <!-- BUG: Button with no accessible label -->
                <button onclick="addToCart(1)"></button>
            </div>
            <div class="product-card">
                <!-- BUG: Missing alt text (a11y) -->
                <img src="https://via.placeholder.com/300x150">
                <h3>Gadget Plus</h3>
                <p>$49.99</p>
                <button onclick="addToCart(2)">Add to Cart</button>
            </div>
            <div class="product-card">
                <!-- BUG: Zero-size image -->
                <img src="" alt="Super Tool" width="0" height="0">
                <h3>Super Tool</h3>
                <p>$19.99</p>
                <button onclick="addToCart(3)">Add to Cart</button>
            </div>
        </div>

        <h2>Contact Us</h2>
        <!-- BUG: Form has required fields but submit returns 500 -->
        <form id="contact-form" onsubmit="return submitForm(event)">
            <label for="email">Email (required):</label>
            <input type="email" id="email" name="email" required placeholder="your@email.com">
            <label for="message">Message:</label>
            <textarea id="message" name="message" placeholder="Your message"></textarea>
            <button type="submit">Send Message</button>
            <div id="form-error" style="color:red; display:none;">Submission failed. Server error.</div>
        </form>

        <div class="error-section">
            <h3>API Status</h3>
            <button onclick="checkBrokenAPI()">Check API</button>
            <div id="api-result"></div>
        </div>
    </main>

    <footer>
        <p>Demo Store &copy; 2024 | <a href="/privacy">Privacy Policy</a></p>
    </footer>

    <script>
        function addToCart(id) {
            // BUG: Makes a request to a broken endpoint
            fetch('/api/cart/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({product_id: id})
            }).then(r => {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            }).catch(e => {
                console.error('Cart error:', e.message);
            });
        }

        function submitForm(e) {
            e.preventDefault();
            // BUG: Submits to endpoint that always returns 500
            fetch('/api/contact', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: document.getElementById('email').value,
                    message: document.getElementById('message').value
                })
            }).then(r => {
                document.getElementById('form-error').style.display = 'block';
            });
            return false;
        }

        function checkBrokenAPI() {
            fetch('/api/broken-endpoint')
                .then(r => r.json())
                .catch(e => {
                    document.getElementById('api-result').textContent = 'Error: ' + e.message;
                    console.error('API error:', e);
                });
        }
    </script>
</body>
</html>"""

_CONTACT_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Contact — Demo Store</title></head>
<body>
<h1>Contact Page</h1>
<p>This page exists but has issues.</p>
<!-- BUG: broken image reference -->
<img src="/broken/path/image.png">
<a href="/">Back to Home</a>
</body>
</html>"""


@demo_app.get("/", response_class=HTMLResponse)
async def demo_home():
    return HTMLResponse(content=_DEMO_HTML)


@demo_app.get("/contact", response_class=HTMLResponse)
async def demo_contact():
    return HTMLResponse(content=_CONTACT_HTML)


@demo_app.get("/products", response_class=HTMLResponse)
async def demo_products():
    return HTMLResponse(content="""<!DOCTYPE html>
<html><head><title>Products</title></head>
<body>
<h1>All Products</h1>
<p>Products page — no products loaded due to API error.</p>
<!-- BUG: This triggers a JS error -->
<script>
  const products = undefined;
  console.error('Products failed to load: ' + products.length);
</script>
<a href="/">Home</a>
</body></html>""")


# BUG endpoint: Always returns 500
@demo_app.post("/api/contact")
async def demo_contact_api():
    return JSONResponse(
        content={"error": "Internal server error — database connection failed"},
        status_code=500,
    )


# BUG endpoint: Always returns 500
@demo_app.post("/api/cart/add")
async def demo_cart_add():
    return JSONResponse(
        content={"error": "Cart service unavailable"},
        status_code=503,
    )


# BUG endpoint: 404
@demo_app.get("/api/broken-endpoint")
async def demo_broken():
    return JSONResponse(
        content={"error": "Not implemented"},
        status_code=501,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(demo_app, host="127.0.0.1", port=8080)
