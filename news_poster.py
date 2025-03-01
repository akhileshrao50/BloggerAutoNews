import requests
from bs4 import BeautifulSoup
from openai import OpenAI  # For content rewriting
from PIL import Image, ImageEnhance
import io
import json
import time
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def fetch_trending_news():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "xml")
    articles = []
    
    for item in soup.find_all("item"):
        title = item.title.text
        link = item.link.text
        if "sport" in title.lower():  # Filter only sports news
            articles.append((title, link))
    
    return articles[:5]  # Fetch top 5 trending sports articles

def scrape_article_content(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")
    paragraphs = soup.find_all("p")
    content = " ".join([p.text for p in paragraphs])
    return content[:2000]  # Limit text length

def rewrite_content(content):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "user", "content": content}
        ]
    )
    return response.choices[0].message.content

def enhance_image(image_url):
    response = requests.get(image_url)
    img = Image.open(io.BytesIO(response.content))
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)
    img_io = io.BytesIO()
    img.save(img_io, format="JPEG")
    return img_io.getvalue()

def upload_image_to_imgbb(image_data):
    api_key = os.getenv("IMGBB_API_KEY")
    url = "https://api.imgbb.com/1/upload"
    
    files = {"image": image_data}
    payload = {"key": api_key}
    response = requests.post(url, files=files, data=payload)
    
    if response.status_code == 200:
        return response.json()["data"]["url"]
    else:
        return None

def post_to_blogger(title, content, image_url):
    blogger_api_url = f"https://www.googleapis.com/blogger/v3/blogs/{os.getenv('BLOGGER_BLOG_ID')}/posts/"
    access_token = os.getenv("BLOGGER_ACCESS_TOKEN")
    
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    post_data = {
        "title": title,
        "content": f"<img src='{image_url}'/><p>{content}</p>",
        "labels": ["Trending", "Sports"]
    }
    
    response = requests.post(blogger_api_url, headers=headers, data=json.dumps(post_data))
    return response.status_code

if __name__ == "__main__":
    while True:
        articles = fetch_trending_news()
        for title, link in articles:
            try:
                content = scrape_article_content(link)
                rewritten_content = rewrite_content(content)
                image_data = enhance_image("SOME_IMAGE_URL")  # Fetch image dynamically
                image_url = upload_image_to_imgbb(image_data)
                if image_url:
                    post_to_blogger(title, rewritten_content, image_url)
                    print(f"Posted: {title}")
                else:
                    print("Image upload failed!")
            except Exception as e:
                print("Error:", e)
        time.sleep(1800)  # Wait 30 minutes before next update
