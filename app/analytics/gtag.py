"""Google gtag.js snippets for Streamlit (parent-frame injection)."""


def _valid_measurement_id(measurement_id: str) -> str | None:
    mid = (measurement_id or "").strip()
    if mid.startswith("G-") and len(mid) > 3:
        return mid
    return None


def parent_frame_gtag_html(measurement_id: str) -> str:
    """
    Install gtag on the top-level Streamlit page.

    Streamlit components run inside iframes. This script tries window.top,
    window.parent, then the component document, with retries until the DOM is ready.
    """
    mid = _valid_measurement_id(measurement_id)
    if not mid:
        return ""

    return f"""<!DOCTYPE html><html><head>
<style>html,body{{margin:0;padding:0;height:0;overflow:hidden;}}</style>
</head><body>
<script>
(function () {{
  var MID = "{mid}";
  var FLAG = "wc_ga_gtag_installed";

  function install(doc) {{
    if (!doc || !doc.head || doc.getElementById(FLAG)) {{
      return false;
    }}

    var loader = doc.createElement("script");
    loader.async = true;
    loader.src = "https://www.googletagmanager.com/gtag/js?id=" + MID;
    doc.head.appendChild(loader);

    var inline = doc.createElement("script");
    inline.id = FLAG;
    inline.text = [
      "window.dataLayer = window.dataLayer || [];",
      "function gtag(){{dataLayer.push(arguments);}}",
      "gtag('js', new Date());",
      "gtag('config', '" + MID + "', {{",
      "  send_page_view: true,",
      "  anonymize_ip: true",
      "}});"
    ].join("\\n");
    doc.head.appendChild(inline);
    return true;
  }}

  function targets() {{
    var docs = [];
    try {{
      if (window.top && window.top.document) docs.push(window.top.document);
    }} catch (e) {{}}
    try {{
      if (window.parent && window.parent.document) docs.push(window.parent.document);
    }} catch (e) {{}}
    docs.push(document);
    return docs;
  }}

  function tryInstall() {{
    var docs = targets();
    for (var i = 0; i < docs.length; i++) {{
      try {{
        if (install(docs[i])) return true;
      }} catch (e) {{}}
    }}
    return false;
  }}

  if (!tryInstall()) {{
    var n = 0;
    var timer = setInterval(function () {{
      n += 1;
      if (tryInstall() || n >= 25) clearInterval(timer);
    }}, 200);
  }}
}})();
</script>
</body></html>"""


def gtag_fragment_html(measurement_id: str) -> str:
    """Minimal fragment fallback (no DOCTYPE) for older component renderers."""
    mid = _valid_measurement_id(measurement_id)
    if not mid:
        return ""
    return parent_frame_gtag_html(mid).replace("<!DOCTYPE html><html><body>", "").replace(
        "</body></html>", ""
    )