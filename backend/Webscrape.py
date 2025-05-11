import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import random
import time

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_LOAD_DIR = os.path.join(SCRIPT_DIR, "LeadOnLamoni")
CSV_FILE = os.path.join(SCRIPT_DIR, "LamoniUrls.csv")
BASE_URL = "https://www.leadonlamoni.com/"
MAX_PAGES = 10000

# Create directory if it doesn't exist
os.makedirs(DOC_LOAD_DIR, exist_ok=True)
print(f"Created directory: {DOC_LOAD_DIR}")

# Web scraping functions
def clean_filename(url):
    """Generate a clean filename from a URL"""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    if not path:
        return "homepage"
    
    # Replace special characters and make it a valid filename
    filename = path.replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '_')
    if len(filename) > 100:  # Avoid overly long filenames
        filename = filename[:100]
    return filename

def is_valid_url(url):
    """Check if a URL should be scraped. Only accept homepage and /vnews/ URLs."""
    if not url:
        return False
        
    parsed = urlparse(url)
    
    # Check if it's within the same domain
    if "leadonlamoni.com" not in parsed.netloc:
        print(f"Skipping non-domain URL: {url}")
        return False
    
    # Only accept the homepage or URLs containing /vnews/
    is_homepage = parsed.path == "/" or parsed.path == ""
    is_vnews = "/vnews/" in parsed.path
    
    if not (is_homepage or is_vnews):
        print(f"Skipping non-vnews URL: {url}")
        return False
    
    # Check for excluded file extensions even within vnews
    excluded_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.mp3', '.mp4', '.avi']
    if any(url.lower().endswith(ext) for ext in excluded_extensions):
        print(f"Skipping excluded file type: {url}")
        return False
    
    return True

def scrape_page(url):
    """Scrape a single page and extract all paragraph text and links"""
    try:
        print(f"Scraping: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return [], "", ""
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No Title"
        
        # Remove unwanted elements
        for element in soup.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style', 'noscript']):
            element.decompose()
            
        # Remove elements with specific classes or IDs that are typically UI elements
        unwanted_classes = [
            'weather', 'navigation', 'menu', 'sidebar', 'footer', 'header',
            'social', 'search', 'dropdown', 'toggle', 'breadcrumbs', 'widget',
            'advertisement', 'banner', 'cookie-notice', 'newsletter','sr-onl'
        ]
        
        for class_name in unwanted_classes:
            for element in soup.find_all(class_=lambda x: x and class_name in x.lower()):
                element.decompose()
        
        # Extract all text content
        content = ""
        
        # Get headings to preserve structure
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        headings_dict = {}
        
        for heading in headings:
            heading_id = heading.get('id', '')
            headings_dict[heading_id] = {
                'tag': heading.name,
                'text': heading.get_text(strip=True),
                'position': heading.sourceline if hasattr(heading, 'sourceline') else 0
            }
        
        # Find all text-containing elements
        text_elements = soup.find_all(['p', 'span', 'div', 'li', 'td', 'th'])
        
        # Process each text element
        for element in text_elements:
            # Skip empty elements
            text = element.get_text(strip=True)
            if not text:
                continue
                
            # Skip if this is a child of another text element we've already processed
            parent_found = False
            for parent in text_elements:
                if parent != element and element in parent.descendants:
                    parent_found = True
                    break
            if parent_found:
                continue
                
            # Skip elements that are likely UI elements
            if any(unwanted in text.lower() for unwanted in ['toggle', 'dropdown', 'search', 'menu', 'weather']):
                continue
                
            # Skip very short text that's likely UI elements
            if len(text) < 3:
                continue
                
            # Try to identify parent sections for better context
            parent_heading = None
            parent_position = 0
            
            # Look for the closest heading above this element
            element_sourceline = element.sourceline if hasattr(element, 'sourceline') else 0
            for heading_id, heading_info in headings_dict.items():
                if heading_info['position'] < element_sourceline and heading_info['position'] > parent_position:
                    parent_heading = heading_info
                    parent_position = heading_info['position']
            
            # Add heading if found and not already added
            if parent_heading and f"# {parent_heading['text']}" not in content:
                heading_level = int(parent_heading['tag'][1])
                markdown_heading = '#' * heading_level + ' ' + parent_heading['text']
                content += markdown_heading + "\n\n"
            
            # Add element text
            content += text + "\n\n"
        
        # Extract links from the page
        links = []
        all_links_count = 0
        valid_links_count = 0
        vnews_links_count = 0
        
        # Find all links on the page
        for a_tag in soup.find_all('a', href=True):
            all_links_count += 1
            link = a_tag['href']
            
            # Skip empty, anchor or javascript links
            if not link or link.startswith('#') or link.startswith('javascript:'):
                continue
            
            # Convert relative links to absolute
            absolute_link = urljoin(url, link)
            
            # Count vnews links separately for debugging
            if "/vnews/" in absolute_link:
                vnews_links_count += 1
            
            if is_valid_url(absolute_link):
                valid_links_count += 1
                links.append(absolute_link)
        
        print(f"Found {all_links_count} total links, {vnews_links_count} vnews links, {valid_links_count} valid links")
                
        return links, content, title
        
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return [], "", "Error Page"

def save_to_markdown(url, content, title):
    """Save the extracted content to a markdown file"""
    try:
        # Ensure the directory exists
        os.makedirs(DOC_LOAD_DIR, exist_ok=True)
        
        filename = clean_filename(url)
        filepath = os.path.join(DOC_LOAD_DIR, f"{filename}.md")
        
        # Add title and metadata to the markdown file
        full_content = f"# {title}\n\n"
        full_content += f"Source URL: {url}\n\n"
        full_content += content
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"Saved file: {filepath}")
        
        # Verify the file was created
        if os.path.exists(filepath):
            print(f"Successfully created file: {filepath}")
        else:
            print(f"WARNING: Failed to verify file creation: {filepath}")
            
        return f"{filename}.md"
    except Exception as e:
        print(f"Error saving markdown file: {e}")
        # Return a placeholder filename in case of error
        return f"error_{clean_filename(url)}.md"

def update_csv(url_data):
    """Update the CSV file with URLs and filenames"""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        if not file_exists:
            writer.writerow(['URL', 'Filename'])
            print(f"Created new CSV file: {CSV_FILE}")
            
        for url, filename in url_data:
            writer.writerow([url, filename])
            print(f"Added to CSV: {url} -> {filename}")

def find_url(csv_file, document_name):
    """
    Search for a document name in a CSV file and return the corresponding URL.
    
    Parameters:
    csv_file (str): Path to the CSV file.
    document_name (str): The name of the document to search for.
    
    Returns:
    str: The corresponding URL if found, otherwise None.
    """
    try:
        if not os.path.exists(csv_file):
            print(f"CSV file not found: {csv_file}")
            return None
            
        df = pd.read_csv(csv_file)
        if df.empty:
            print(f"CSV file is empty: {csv_file}")
            return None
            
        result = df.loc[df.iloc[:, 1] == document_name, df.columns[0]]
        return result.values[0] if not result.empty else None
    except Exception as e:
        print(f"Error finding URL: {e}")
        return None
    
def find_vnews_url_on_homepage():
    """Find all vnews URLs on the homepage"""
    print("Looking for vnews links on the homepage...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(BASE_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Failed to fetch homepage: Status code {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        vnews_links = []
        
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            absolute_link = urljoin(BASE_URL, link)
            
            if "/vnews/" in absolute_link and absolute_link not in vnews_links:
                vnews_links.append(absolute_link)
                print(f"Found vnews link: {absolute_link}")
        
        print(f"Found {len(vnews_links)} vnews links on homepage")
        return vnews_links
    
    except Exception as e:
        print(f"Error finding vnews links on homepage: {e}")
        return []

def scrape_website():
    """Scrape the website and save content to markdown files"""
    print(f"Starting to scrape {BASE_URL}")
    start_time = time.time()
    
    visited_urls = set()
    url_queue = [BASE_URL]  # Start with homepage
    extracted_pages = []
    
    # First find all vnews links on the homepage and add them to the queue
    vnews_links = find_vnews_url_on_homepage()
    for link in vnews_links:
        if link not in url_queue:
            url_queue.append(link)
    
    print(f"Initial queue has {len(url_queue)} URLs")
    
    while url_queue and len(visited_urls) < MAX_PAGES:
        # Get next URL to process
        current_url = url_queue.pop(0)
        
        if current_url in visited_urls:
            continue
        
        # Add to visited set
        visited_urls.add(current_url)
        
        # Scrape the page
        new_links, content, title = scrape_page(current_url)
        
        if content:  # Save all pages that have any content
            # Save content to markdown
            filename = save_to_markdown(current_url, content, title)
            
            # Add to extracted pages list
            extracted_pages.append((current_url, filename))
            
            # Update CSV immediately after saving each file
            update_csv([(current_url, filename)])
        else:
            print(f"No content extracted from {current_url}")
        
        # Add new links to the queue - but only vnews links or homepage
        links_added = 0
        for link in new_links:
            if link not in visited_urls and link not in url_queue:
                # Double-check that it's a valid URL (homepage or vnews)
                parsed = urlparse(link)
                is_homepage = parsed.path == "/" or parsed.path == ""
                is_vnews = "/vnews/" in parsed.path
                
                if is_homepage or is_vnews:
                    url_queue.append(link)
                    links_added += 1
        
        print(f"Added {links_added} new URLs to the queue. Queue size: {len(url_queue)}")
        
        # Add some delay to be respectful
        delay = random.uniform(1.0, 2.0)
        print(f"Waiting {delay:.2f} seconds before next request")
        time.sleep(delay)
        
        print(f"Progress: {len(visited_urls)}/{MAX_PAGES} pages processed, {len(extracted_pages)} pages extracted")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\nScraping completed. Processed {len(visited_urls)} pages in {elapsed_time:.2f} seconds.")
    print(f"Extracted content saved to {len(extracted_pages)} files in {DOC_LOAD_DIR}")
    print(f"URL tracking updated in {CSV_FILE}")
    
    # Print summary of scraped pages
    print("\nSummary of scraped pages:")
    for i, (url, filename) in enumerate(extracted_pages, 1):
        print(f"{i}. {url} -> {filename}")
    
    # List all vnews files separately
    vnews_files = [(url, filename) for url, filename in extracted_pages if "/vnews/" in url]
    
    print(f"\nTotal vnews pages found: {len(vnews_files)}")
    for i, (url, filename) in enumerate(vnews_files, 1):
        print(f"{i}. {url}")
    
    return len(extracted_pages)


# Main execution
if __name__ == "__main__":
    process_start = time.time()
    
    # Step 1: Scrape the website
    print("=== STEP 1: SCRAPING WEBSITE ===")
    num_pages = scrape_website()
    
    process_end = time.time()
    elapsed_time = process_end - process_start
    
    # Convert to days, hours, minutes, and seconds
    days = int(elapsed_time // (24 * 3600))
    elapsed_time %= (24 * 3600)
    hours = int(elapsed_time // 3600)
    elapsed_time %= 3600
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60

    print(f"Completed scraping with {num_pages} pages extracted")
    print(f"\nTotal process execution time: {days} days, {hours} hours, {minutes} minutes, and {seconds:.2f} seconds")
