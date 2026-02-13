import os
import sys
import re
import datetime
import shutil

# Try importing markdown, else warn user
try:
    import markdown
except ImportError:
    print("[-] Error: 'markdown' library not found.")
    print("[-] Please install it using: pip install markdown")
    sys.exit(1)

TEMPLATE_PATH = "templates/writeup-template.html"
OUTPUT_DIR = "writeups"
ASSETS_IMG_DIR = "assets/img"

def process_images(md_content, source_file_path):
    """
    Finds image references in markdown, copies images to assets/img,
    and updates the markdown to use correct relative paths.
    """
    # Get the directory of the source markdown file
    source_dir = os.path.dirname(os.path.abspath(source_file_path))
    
    # Create assets/img directory if it doesn't exist
    if not os.path.exists(ASSETS_IMG_DIR):
        os.makedirs(ASSETS_IMG_DIR)
    
    # Pattern to match markdown images: ![alt text](path)
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def replace_image_path(match):
        alt_text = match.group(1)
        original_path = match.group(2)
        
        # Skip if it's already pointing to assets/img or is a URL
        if original_path.startswith('http://') or original_path.startswith('https://'):
            return match.group(0)  # Keep URL as-is
        if original_path.startswith('../assets/img/'):
            return match.group(0)  # Already correct path
        
        # Resolve the actual image path (could be relative to markdown file)
        if os.path.isabs(original_path):
            source_image_path = original_path
        else:
            source_image_path = os.path.join(source_dir, original_path)
        
        # Check if the image file exists
        if not os.path.exists(source_image_path):
            print(f"[!] Warning: Image not found: {source_image_path}")
            return match.group(0)  # Keep original if file doesn't exist
        
        # Get the image filename
        image_filename = os.path.basename(source_image_path)
        
        # Copy image to assets/img
        dest_image_path = os.path.join(ASSETS_IMG_DIR, image_filename)
        
        try:
            shutil.copy2(source_image_path, dest_image_path)
            print(f"[+] Copied image: {image_filename} -> {ASSETS_IMG_DIR}/")
        except Exception as e:
            print(f"[!] Error copying image {image_filename}: {e}")
            return match.group(0)
        
        # Return updated markdown with correct relative path (from writeups/ to assets/img)
        new_path = f"../assets/img/{image_filename}"
        return f"![{alt_text}]({new_path})"
    
    # Replace all image references
    updated_content = re.sub(image_pattern, replace_image_path, md_content)
    return updated_content

def parse_frontmatter(content):
    """
    Extracts YAML-style frontmatter from the markdown content.
    Returns metadata dict and the remaining markdown content.
    """
    meta = {
        "title": "Untitled Writeup",
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "category": "General",
        "author": "Alterpix"
    }
    
    # Regex to find frontmatter between ---
    frontmatter_pattern = r"^---\s+(.*?)\s+---\s+(.*)$"
    match = re.search(frontmatter_pattern, content, re.DOTALL)
    
    if match:
        frontmatter_str = match.group(1)
        markdown_content = match.group(2)
        
        # Simple YAML parsing (key: value)
        for line in frontmatter_str.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip().lower()] = value.strip().strip('"').strip("'")
        
        return meta, markdown_content
    else:
        return meta, content

def convert_to_html(md_content):
    """Converts markdown text to HTML with Terminal Card style for code blocks."""
    # Extensions: extra (tables, fences), codehilite
    html = markdown.markdown(md_content, extensions=['extra', 'codehilite', 'fenced_code'])
    
    # regex pattern to find codehilite divs
    pattern = r'(<div class="codehilite">)(.*?)(</div>)'
    
    def replacement(match):
        code_block = match.group(0) # The full <div class="codehilite">...</div>
        content = match.group(2)
        
        # Remove HTML tags to check text content
        text_content = re.sub(r'<[^>]+>', '', content)
        
        # Simple heuristic to determine title
        title = "TERMINAL"
        if "nmap" in text_content or "sudo" in text_content or "$ " in text_content or "bash" in text_content:
            title = "BASH_SHELL"
        elif "python" in text_content or "def " in text_content or "print(" in text_content:
            title = "PYTHON_SCRIPT"
            
        return f"""<div class="code-terminal">
    <div class="terminal-header">
        <div class="dot red"></div>
        <div class="dot yellow"></div>
        <div class="dot green"></div>
        <div class="title">{title}</div>
    </div>
    <div class="terminal-body">{code_block}</div>
</div>"""

    return re.sub(pattern, replacement, html, flags=re.DOTALL)

def process_file(input_file):
    if not os.path.exists(input_file):
        print(f"[-] Error: File '{input_file}' not found.")
        return

    print(f"[+] Processing {input_file}...")
    
    with open(input_file, "r", encoding="utf-8") as f:
        full_content = f.read()
    
    meta, md_content = parse_frontmatter(full_content)
    
    # Process images: copy to assets/img and update paths
    md_content = process_images(md_content, input_file)
    
    html_content = convert_to_html(md_content)
    
    # Read Template
    if not os.path.exists(TEMPLATE_PATH):
        print(f"[-] Error: Template '{TEMPLATE_PATH}' not found.")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    
    # Inject Metadata
    output_html = template.replace("[TITLE]", meta.get("title", "Untitled"))
    output_html = output_html.replace("[WRITEUP TITLE HERE]", meta.get("title", "Untitled"))
    output_html = output_html.replace("[YYYY-MM-DD]", meta.get("date", "YYYY-MM-DD"))
    output_html = output_html.replace("[WEB/NETWORK/CTF]", meta.get("category", "Uncategorized"))
    output_html = output_html.replace("Alterpix", meta.get("author", "Alterpix"))
    
    # Inject Content
    output_html = output_html.replace("{{ CONTENT }}", html_content)
    
    # Save Output
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    filename = os.path.basename(input_file).replace(".md", ".html")
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
    print(f"[+] Successfully generated: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/convert.py <path_to_markdown_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    process_file(input_file)
