import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import xml.etree.ElementTree as ET
from xml.dom import minidom

def get_article_date(article_url):
    """Pobiera datę artykułu ze strony szczegółów"""
    try:
        response = requests.get(article_url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Szukamy meta tag z datą publikacji
        date_meta = soup.find('meta', {'property': 'article:published_time'})
        if date_meta and date_meta.get('content'):
            return date_meta['content']
        
        # Alternatywnie szukamy w time tag
        time_tag = soup.find('time', {'class': 'article__date'})
        if time_tag and time_tag.get('datetime'):
            return time_tag['datetime']
            
    except Exception as e:
        print(f"Error getting date for {article_url}: {e}")
    
    return None

def scrape_bankier_news():
    """Scrapuje pierwsze 2 strony wiadomości z Bankier.pl"""
    articles = []
    base_url = "https://www.bankier.pl/wiadomosc/"
    
    for page in range(1, 3):  # Strony 1 i 2
        try:
            url = f"{base_url}?page={page}" if page > 1 else base_url
            print(f"Scraping: {url}")
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Szukamy artykułów - różne możliwe selektory
            article_items = soup.find_all('article', class_='entry')
            if not article_items:
                article_items = soup.find_all('div', class_='article')
            
            for item in article_items:
                try:
                    # Tytuł i link
                    title_tag = item.find('a', class_='entry__title')
                    if not title_tag:
                        title_tag = item.find('h2').find('a') if item.find('h2') else None
                    
                    if not title_tag:
                        continue
                    
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    # Upewniamy się, że link jest pełny
                    if link.startswith('/'):
                        link = f"https://www.bankier.pl{link}"
                    
                    # Opis
                    desc_tag = item.find('div', class_='entry__lead')
                    if not desc_tag:
                        desc_tag = item.find('p', class_='article__lead')
                    description = desc_tag.get_text(strip=True) if desc_tag else ""
                    
                    # Data publikacji
                    pub_date = get_article_date(link)
                    if not pub_date:
                        # Jeśli nie udało się pobrać daty, używamy aktualnej
                        warsaw_tz = pytz.timezone('Europe/Warsaw')
                        pub_date = datetime.now(warsaw_tz).isoformat()
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'pub_date': pub_date
                    })
                    
                    print(f"Added: {title[:50]}...")
                    
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
            
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
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
    print("Starting Bankier.pl RSS scraper...")
    
    # Scrapowanie artykułów
    articles = scrape_bankier_news()
    print(f"\nScraped {len(articles)} articles")
    
    if articles:
        # Generowanie RSS
        rss_content = generate_rss(articles)
        
        # Zapis do pliku
        with open('rss.xml', 'w', encoding='utf-8') as f:
            f.write(rss_content)
        
        print("RSS feed generated successfully!")
    else:
        print("No articles found!")

if __name__ == "__main__":
    main()