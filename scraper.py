import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time

def get_article_date(article_url, headers):
    """Pobiera datę artykułu ze strony szczegółów"""
    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Szukamy meta tag z datą publikacji
        date_meta = soup.find('meta', {'property': 'article:published_time'})
        if date_meta and date_meta.get('content'):
            return date_meta['content']
        
        # Alternatywnie szukamy w time tag
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            return time_tag['datetime']
            
    except Exception as e:
        print(f"Error getting date for {article_url}: {e}")
    
    return None

def scrape_bankier_news():
    """Scrapuje pierwsze 2 strony wiadomości z Bankier.pl"""
    articles = []
    base_url = "https://www.bankier.pl/wiadomosc/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    for page in range(1, 3):  # Strony 1 i 2
        try:
            url = f"{base_url}?page={page}" if page > 1 else base_url
            print(f"\nScraping: {url}")
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            print(f"Response status: {response.status_code}")
            print(f"Response length: {len(response.content)} bytes")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Próbujemy różne selektory dla artykułów
            article_items = []
            
            # Próba 1: Szukamy article z klasą entry
            article_items = soup.find_all('article', class_='entry')
            print(f"Found {len(article_items)} articles with class 'entry'")
            
            # Próba 2: Jeśli nie znaleziono, szukamy div z klasą article
            if not article_items:
                article_items = soup.find_all('div', class_='article')
                print(f"Found {len(article_items)} articles with class 'article'")
            
            # Próba 3: Szukamy wszystkich linków do wiadomości
            if not article_items:
                links = soup.find_all('a', href=lambda h: h and '/wiadomosc/' in h and h != '/wiadomosc/')
                print(f"Found {len(links)} links with '/wiadomosc/' in href")
                
                # Tworzymy pseudo-artykuły z linków
                for link in links[:20]:  # Max 20 na stronę
                    article_items.append(link.parent if link.parent else link)
            
            print(f"Total article items to process: {len(article_items)}")
            
            for idx, item in enumerate(article_items[:20], 1):  # Max 20 artykułów na stronę
                try:
                    print(f"\nProcessing article {idx}...")
                    
                    # Szukamy tytułu i linku
                    title_tag = None
                    link = None
                    
                    # Próba 1: Link z klasą entry__title
                    title_tag = item.find('a', class_='entry__title')
                    
                    # Próba 2: Link w h2 lub h3
                    if not title_tag:
                        for heading in ['h2', 'h3', 'h4']:
                            heading_tag = item.find(heading)
                            if heading_tag:
                                title_tag = heading_tag.find('a')
                                if title_tag:
                                    break
                    
                    # Próba 3: Jakikolwiek link do wiadomości
                    if not title_tag:
                        title_tag = item.find('a', href=lambda h: h and '/wiadomosc/' in h)
                    
                    # Próba 4: Jeśli item SAM jest linkiem
                    if not title_tag and item.name == 'a':
                        title_tag = item
                    
                    if not title_tag:
                        print(f"  ✗ No title tag found")
                        continue
                    
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href', '')
                    
                    if not link or not title:
                        print(f"  ✗ Missing title or link")
                        continue
                    
                    # Upewniamy się, że link jest pełny
                    if link.startswith('/'):
                        link = f"https://www.bankier.pl{link}"
                    
                    # Opis
                    description = ""
                    desc_tag = item.find('div', class_='entry__lead')
                    if not desc_tag:
                        desc_tag = item.find('p', class_='article__lead')
                    if not desc_tag:
                        desc_tag = item.find('p')
                    
                    if desc_tag:
                        description = desc_tag.get_text(strip=True)
                    
                    # Data publikacji - pobieramy z podstrony (wolniejsze, ale dokładniejsze)
                    pub_date = None
                    
                    # Najpierw sprawdzamy czy data jest na liście
                    time_tag = item.find('time')
                    if time_tag and time_tag.get('datetime'):
                        pub_date = time_tag['datetime']
                        print(f"  ✓ Date from list page: {pub_date}")
                    
                    # Jeśli nie, pobieramy ze strony artykułu
                    if not pub_date:
                        time.sleep(0.5)  # Żeby nie spamować
                        pub_date = get_article_date(link, headers)
                        if pub_date:
                            print(f"  ✓ Date from article page: {pub_date}")
                    
                    # Jeśli nadal nie ma daty, używamy aktualnej
                    if not pub_date:
                        warsaw_tz = pytz.timezone('Europe/Warsaw')
                        pub_date = datetime.now(warsaw_tz).isoformat()
                        print(f"  ⚠ Using current date: {pub_date}")
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'pub_date': pub_date
                    })
                    
                    print(f"  ✓ Added: {title[:60]}...")
                    
                except Exception as e:
                    print(f"  ✗ Error parsing article: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
        except Exception as e:
            print(f"✗ Error scraping page {page}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return articles

def generate_rss(articles):
    """Generuje plik RSS z artykułów"""
    warsaw_tz = pytz.timezone('Europe/Warsaw')
    now = datetime.now(warsaw_tz)
    
    # Tworzenie RSS
    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    
    channel = ET.SubElement(rss, 'channel')
    
    # Metadane kanału
    ET.SubElement(channel, 'title').text = 'Bankier.pl - Wiadomości'
    ET.SubElement(channel, 'link').text = 'https://www.bankier.pl/wiadomosc/'
    ET.SubElement(channel, 'description').text = 'Najnowsze wiadomości z Bankier.pl'
    ET.SubElement(channel, 'language').text = 'pl'
    ET.SubElement(channel, 'lastBuildDate').text = now.strftime('%a, %d %b %Y %H:%M:%S %z')
    
    # Dodanie artykułów
    for article in articles:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = article['title']
        ET.SubElement(item, 'link').text = article['link']
        ET.SubElement(item, 'description').text = article['description']
        ET.SubElement(item, 'guid').text = article['link']
        
        # Konwersja daty do formatu RFC 822
        try:
            if 'T' in article['pub_date']:  # ISO format
                dt = datetime.fromisoformat(article['pub_date'].replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = warsaw_tz.localize(dt)
                pub_date_str = dt.strftime('%a, %d %b %Y %H:%M:%S %z')
            else:
                pub_date_str = article['pub_date']
            
            ET.SubElement(item, 'pubDate').text = pub_date_str
        except Exception as e:
            print(f"Error formatting date: {e}")
            ET.SubElement(item, 'pubDate').text = now.strftime('%a, %d %b %Y %H:%M:%S %z')
    
    # Formatowanie XML
    xml_str = ET.tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Usunięcie pustych linii
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
    
    return pretty_xml

def main():
    print("=" * 70)
    print("Starting Bankier.pl RSS scraper...")
    print(f"Current time: {datetime.now()}")
    print("=" * 70)
    
    # Scrapowanie artykułów
    articles = scrape_bankier_news()
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: Scraped {len(articles)} articles")
    print("=" * 70)
    
    if articles:
        # Generowanie RSS
        rss_content = generate_rss(articles)
        
        # Zapis do pliku
        with open('rss.xml', 'w', encoding='utf-8') as f:
            f.write(rss_content)
        
        print(f"\n✓ RSS feed generated successfully!")
        print(f"✓ File size: {len(rss_content)} bytes")
        print(f"✓ Articles in feed: {len(articles)}")
    else:
        print("\n⚠ WARNING: No articles found!")
        print("Creating empty RSS feed for debugging...")
        
        # Tworzymy pusty feed żeby zobaczyć że workflow działa
        rss_content = generate_rss([])
        with open('rss.xml', 'w', encoding='utf-8') as f:
            f.write(rss_content)
        
        print("✓ Empty RSS feed created.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
