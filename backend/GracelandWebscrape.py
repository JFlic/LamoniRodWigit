
# This script doesn't work anymore I'm pretty sure Graceland updated there webscrape firewall becasue of me :(

import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import csv
import random
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DOC_LOAD_DIR = r"GracelandWebsite"
CSV_FILE = "LamoniUrls.csv"
BASE_URL = "https://www.graceland.edu/"
MAX_PAGES = 10000
DELAY_RANGE = (2.0, 5.0)  # Increased delay between requests

# Create session with retry strategy
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# Make sure directory exists
if not os.path.exists(DOC_LOAD_DIR):
    os.makedirs(DOC_LOAD_DIR, exist_ok=True)

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
    """Check if a URL should be scraped"""
    parsed = urlparse(url)
    
    # Check if it's within the same domain
    if "graceland.edu" not in parsed.netloc:
        return False
    
    # Check for excluded file extensions
    excluded_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.mp3', '.mp4', '.avi']
    if any(url.lower().endswith(ext) for ext in excluded_extensions):
        return False
    
    return True

def get_random_user_agent():
    """Return a random, realistic user agent string"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/120.0.2210.77"
    ]
    return random.choice(user_agents)

def scrape_page(url, session):
    """Scrape a single page and extract all paragraph text and links"""
    try:
        logger.info(f"Scraping: {url}")
        
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "TE": "trailers"
        }
        
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {url}: Status code {response.status_code}")
            return [], "", ""
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No Title"
        
        # Extract all paragraph text
        paragraphs = soup.find_all('p')
        content = ""
        
        # Get headings to preserve structure
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        headings_dict = {}
        
        for heading in headings:
            heading_id = heading.get('id', '')
            headings_dict[heading_id] = {
                'tag': heading.name,
                'text': heading.get_text(strip=True),
                'position': heading.sourceline
            }
        
        # Process each paragraph
        for paragraph in paragraphs:
            # Skip empty paragraphs
            text = paragraph.get_text(strip=True)
            if not text:
                continue
                
            # Try to identify parent sections for better context
            parent_heading = None
            parent_position = 0
            
            # Look for the closest heading above this paragraph
            for heading_id, heading_info in headings_dict.items():
                if heading_info['position'] < paragraph.sourceline and heading_info['position'] > parent_position:
                    parent_heading = heading_info
                    parent_position = heading_info['position']
            
            # Add heading if found and not already added
            if parent_heading and f"# {parent_heading['text']}" not in content:
                heading_level = int(parent_heading['tag'][1])
                markdown_heading = '#' * heading_level + ' ' + parent_heading['text']
                content += markdown_heading + "\n\n"
            
            # Add paragraph text
            content += text + "\n\n"
        
        # Extract list items (<li> tags) as they often contain valuable content
        list_items = soup.find_all('li')
        if list_items:
            content += "\n## Additional List Items\n\n"
            for item in list_items:
                item_text = item.get_text(strip=True)
                if item_text:
                    content += "- " + item_text + "\n"
        
        # Extract links from the page
        links = []
        for a_tag in soup.find_all('a', href=True):
            link = a_tag['href']
            absolute_link = urljoin(url, link)
            
            if is_valid_url(absolute_link):
                links.append(absolute_link)
                
        return links, content, title
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return [], "", "Error Page"

def save_to_markdown(url, content, title):
    """Save the extracted content to a markdown file"""
    filename = clean_filename(url)
    filepath = os.path.join(DOC_LOAD_DIR, f"{filename}.md")
    
    # Add title and metadata to the markdown file
    full_content = f"# {title}\n\n"
    full_content += f"Source URL: {url}\n\n"
    full_content += content
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        return f"{filename}.md"
    except Exception as e:
        logger.error(f"Error saving file {filepath}: {str(e)}")
        return None

def update_csv(url_data):
    """Update the CSV file with URLs and filenames"""
    file_exists = os.path.isfile(CSV_FILE)
    
    try:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            if not file_exists:
                writer.writerow(['URL', 'Filename'])
                
            for url, filename in url_data:
                if filename:  # Only add entries with valid filenames
                    writer.writerow([url, filename])
    except Exception as e:
        logger.error(f"Error updating CSV file: {str(e)}")

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
            logger.warning(f"CSV file {csv_file} does not exist")
            return None
            
        df = pd.read_csv(csv_file)
        result = df.loc[df.iloc[:, 1] == document_name, df.columns[0]]
        return result.values[0] if not result.empty else None
    except Exception as e:
        logger.error(f"Error finding URL: {e}")
        return None
    
def scrape_website():
    """Scrape the website and save content to markdown files"""
    logger.info(f"Starting to scrape {BASE_URL}")
    start_time = time.time()
    
    # Create a persistent session to maintain cookies
    session = create_session()
    
    # First, try to fetch the homepage to establish cookies
    try:
        logger.info("Initial connection attempt to establish session cookies...")
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.google.com/",  # Pretend we're coming from Google search
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        init_response = session.get(BASE_URL, headers=headers, timeout=15)
        if init_response.status_code != 200:
            logger.warning(f"Initial connection failed with status code {init_response.status_code}")
            if init_response.status_code == 403:
                logger.warning("Website may have strong anti-scraping measures in place")
    except Exception as e:
        logger.error(f"Error during initial connection: {str(e)}")
    
    visited_urls = set()
    url_queue = [BASE_URL]
    extracted_pages = []
    
    while url_queue and len(visited_urls) < MAX_PAGES:
        # Get next URL to process
        current_url = url_queue.pop(0)
        
        if current_url in visited_urls:
            continue
        
        # Add to visited set
        visited_urls.add(current_url)
        
        # Scrape the page
        new_links, content, title = scrape_page(current_url, session)
        
        if content:  # Save all pages that have any content
            # Save content to markdown
            filename = save_to_markdown(current_url, content, title)
            if filename:
                extracted_pages.append((current_url, filename))
        
        # Add new links to the queue
        for link in new_links:
            if link not in visited_urls and link not in url_queue:
                url_queue.append(link)
        
        # Add delay to be respectful and avoid detection
        delay = random.uniform(DELAY_RANGE[0], DELAY_RANGE[1])
        logger.debug(f"Waiting {delay:.2f} seconds before next request")
        time.sleep(delay)
        
        if len(visited_urls) % 10 == 0:
            logger.info(f"Progress: {len(visited_urls)}/{MAX_PAGES} pages processed, {len(extracted_pages)} pages saved")
    
    # Update the CSV with all the new files
    update_csv(extracted_pages)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Scraping completed. Processed {len(visited_urls)} pages in {elapsed_time:.2f} seconds.")
    logger.info(f"Extracted content saved to {len(extracted_pages)} files in {DOC_LOAD_DIR}")
    logger.info(f"URL tracking updated in {CSV_FILE}")
    
    return len(extracted_pages)


# Main execution
if __name__ == "__main__":
    process_start = time.time()
    
    # Step 1: Scrape the website
    print("=== STEP 1: SCRAPING WEBSITE ===")
    try:
        num_pages = scrape_website()
        print(f"Completed scraping with {num_pages} pages extracted")
    except Exception as e:
        logger.error(f"Fatal error during scraping: {str(e)}")
        print(f"Scraping failed with error: {str(e)}")