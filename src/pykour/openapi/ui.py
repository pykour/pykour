"""Swagger UI and ReDoc HTML templates."""


def get_swagger_ui_html(
    openapi_url: str,
    title: str,
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    swagger_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
) -> str:
    """Generate Swagger UI HTML page.

    Args:
        openapi_url: URL to OpenAPI JSON schema.
        title: Page title.
        swagger_js_url: URL to Swagger UI JavaScript bundle.
        swagger_css_url: URL to Swagger UI CSS.
        swagger_favicon_url: URL to favicon.

    Returns:
        HTML string.
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="{swagger_css_url}">
    <link rel="icon" type="image/png" href="{swagger_favicon_url}">
    <style>
        html {{
            box-sizing: border-box;
            overflow-y: scroll;
        }}
        *,
        *:before,
        *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin: 0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="{swagger_js_url}"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: "{openapi_url}",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout",
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true
            }});
            window.ui = ui;
        }};
    </script>
</body>
</html>
"""


def get_redoc_html(
    openapi_url: str,
    title: str,
    redoc_js_url: str = "https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js",
    redoc_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
) -> str:
    """Generate ReDoc HTML page.

    Args:
        openapi_url: URL to OpenAPI JSON schema.
        title: Page title.
        redoc_js_url: URL to ReDoc JavaScript bundle.
        redoc_favicon_url: URL to favicon.

    Returns:
        HTML string.
    """
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - ReDoc</title>
    <link rel="icon" type="image/png" href="{redoc_favicon_url}">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url="{openapi_url}"></redoc>
    <script src="{redoc_js_url}"></script>
</body>
</html>
"""
