"""Google gtag.js snippet for Streamlit (injects into parent document)."""


def parent_frame_gtag_html(measurement_id: str) -> str:
    """
    Install gtag on the Streamlit parent page so Google's tag checker detects it.

    Streamlit renders components inside iframes; scripts in the iframe are invisible
    to Google Tag Assistant. This script escapes into window.parent.document.
    """
    # Measurement IDs are always G-XXXXXXXX — safe to embed after strip check
    mid = measurement_id.strip()
    if not mid.startswith("G-"):
        return ""

    return f"""<!DOCTYPE html><html><head></head><body>
<script>
(function () {{
  var MID = "{mid}";
  var FLAG = "wc_ga_gtag_installed";

  function install(doc) {{
    if (!doc || doc.getElementById(FLAG)) return;

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
      "  anonymize_ip: true,",
      "  page_title: 'WorldCup Analyst',",
      "  page_location: window.parent.location.href",
      "}});"
    ].join("\\n");
    doc.head.appendChild(inline);
  }}

  try {{
    install(window.parent.document);
  }} catch (err) {{
    install(document);
  }}
}})();
</script>
</body></html>"""