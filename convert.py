#%%
import requests
import json
import os
import re

# Make sure you have the AnkiConnect add-on installed on your local Anki

# AnkiConnect API endpoint
ANKI_CONNECT_URL = "http://localhost:8765"

def anki_connect(action, **params):
    """Send a request to AnkiConnect and return the response."""
    request_json = {"action": action, "version": 6, "params": params}
    try:
        response = requests.post(ANKI_CONNECT_URL, json=request_json)
        response.raise_for_status()
        result = response.json()
        if result.get("error"):
            raise Exception(f"AnkiConnect error: {result['error']}")
        return result["result"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to AnkiConnect: {e}")

def get_deck_names():
    """Retrieve all deck names from Anki."""
    return anki_connect("deckNames")

def get_notes_in_deck(deck_name):
    """Retrieve all notes in a specific deck."""
    note_ids = anki_connect("findNotes", query=f'deck:"{deck_name}"')
    if not note_ids:
        return []
    notes_info = anki_connect("notesInfo", notes=note_ids)
    return notes_info

def clean_field(field):
    """Convert HTML to Markdown using html2text, then replace - with • for bullet points, and remove extra blank lines between bullets. Also unescape - if needed. Uses html2text config to minimize blank lines and set bullet char."""
    import html2text
    import re
    import html
    if field is None:
        return ""
    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap lines
    h.single_line_break = True  # Only one line break for <br>
    h.ignore_links = False
    h.ignore_images = True
    h.ignore_emphasis = False
    h.bypass_tables = False
    h.ul_item_mark = '•'  # Use • for bullets
    h.protect_links = True
    h.skip_internal_links = True
    h.mark_code = False
    h.google_doc = False
    h.pad_tables = False
    h.ignore_tables = True
    h.list_indent = 0
    h.unicode_snob = True
    md = h.handle(field)

    return md.strip()

def sanitize_filename(name):
    """Sanitize the name to be safe for file system."""
    name = name.replace(" ", "_")
    allowed_chars = r'a-zA-Z0-9\-_.\u00C0-\u017F'
    sanitized = ''.join(c if re.match(f'[{allowed_chars}]', c) else '_' for c in name)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    if not sanitized:
        sanitized = 'unnamed'
    return sanitized

def truncate_title(title, max_length=200):
    """Truncate the title to a maximum length, preferably at a word boundary."""
    if len(title) <= max_length:
        return title
    # Find the last space before max_length
    space_index = title.rfind(' ', 0, max_length)
    if space_index != -1:
        return title[:space_index]
    else:
        return title[:max_length]

def main():
    try:
        # Fetch all deck names from Anki
        deck_names = get_deck_names()
        if not deck_names:
            print("No decks found in Anki.")
            return

        # Output directory for Markdown files
        output_dir = "markdown_output"
        os.makedirs(output_dir, exist_ok=True)

        # Process each deck
        for deck_name in deck_names:
            print(f"Processing deck: {deck_name}")
            notes = get_notes_in_deck(deck_name)
            if not notes:
                print(f"No notes found in deck: {deck_name}")
                continue

            # Create directory structure based on deck hierarchy
            parts = deck_name.split("::")
            sanitized_parts = [sanitize_filename(part) for part in parts if part]
            directory_path = os.path.join(output_dir, *sanitized_parts)
            os.makedirs(directory_path, exist_ok=True)

            # Track title counts to handle duplicates within this deck
            title_counts = {}

            # Process each note in the deck
            for note in notes:
                fields = note.get("fields", {})
                front = fields.get("Front", {}).get("value", "")
                back = fields.get("Back", {}).get("value", "")
                note_id = note.get("noteId")

                # Determine the title
                if front:
                    title = clean_field(front)
                    truncated_title = truncate_title(title, max_length=200)
                else:
                    truncated_title = f"Note_{note_id}"

                # Determine the content (e.g., link or text)
                content = clean_field (back) if back else ""

                # Create a safe filename from the truncated title
                base_filename = sanitize_filename(truncated_title)

                # Handle duplicate titles within the same deck
                count = title_counts.get(base_filename, 0)
                if count > 0:
                    filename = f"{base_filename}_{count}.md"
                else:
                    filename = f"{base_filename}.md"
                title_counts[base_filename] = count + 1

                # Construct the full file path
                full_path = os.path.join(directory_path, filename)

                # Write the Markdown file
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n{content}\n")
                print(f"Saved note {note_id} to {full_path}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
# %%
