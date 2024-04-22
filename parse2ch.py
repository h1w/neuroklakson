from bs4 import BeautifulSoup
import requests

async def parseTredToPostTextList(url):
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles_with_target_class = soup.find_all('article', class_='post__message')
            
            texts_list = []
            for article in articles_with_target_class:
                all_a_tags_in_article = article.find_all('a')
                for a_tag in all_a_tags_in_article:
                    a_tag.decompose()
                article_text = article.get_text(strip=True)
                
                texts_list.append(article_text)

            return texts_list
        else:
            return None
    except:
        pass
    finally:
        pass