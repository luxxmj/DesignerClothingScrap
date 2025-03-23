import pandas as pd
from bs4 import BeautifulSoup
import time
import re
import requests
from selenium.webdriver import Firefox, FirefoxOptions
# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# Luxury clothing brands to scrape from; ranks wont go into any data just for organization
s_brands = ["Bottega Veneta", "Louis Vuitton"]
a_brands = ["Prada", "Marni"]
b_brands = ["Burberry", "YSL"]
c_brands = ["Versace", "Polo Ralph Lauren"]
# Street clothing brands to scrape from; ranks wont go into any data just for organization, tbf
ss_brands = ["MNML", '']
aa_brands = ['', '']
bb_brands = ['', '']
cc_brands = ['', '']

options = FirefoxOptions()
options.headless = True
driver = Firefox(options=options)

x = True # minitoggle- when ran, scraping mnml site's (streetwear) {not prada's site (luxury)}

# Prada men's outerwear collection
prada_outerwear = "https://www.prada.com/us/en/mens/ready-to-wear/outerwear/c/10136US"

# Mnml's denim collection, (can /products.json since backend is shopify)
mnml_denim = "https://mnml.la/collections/denim/products.json?limit=1000"

headers = {
    # Insert user agent in a string (you can google yours)
}

# For excluding a certain nested listed item (unavailable size item)
def size_available(tag):
    return tag.name == "li" and not tag.find("button", disabled=True)

def main():
    products = []
    
    if not x:
        # Get page, accept cookies, and expand page to see all items
        driver.get(prada_outerwear)
        driver.implicitly_wait(5)
        button = driver.find_element(By.XPATH, "//*[@aria-label='Show more']")
        driver.find_element(By.CLASS_NAME, "banner_cta").click()
        
        # Get expected product amount on page
        amtEle = driver.find_element(By.TAG_NAME, "p")
        print(amtEle.get_attribute('class'))
        amt = int(amtEle.text[: amtEle.text.find(" ")])
        
        button.click()
        
        # Scroll page until all items found (infinite scrolling javascript)
        while True:
            soup = BeautifulSoup(driver.page_source, "lxml")
            items = soup.find_all("a", class_="h-full product-card__link")
            if not len(items) == amt:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            else:
                break
    
        # For each product, request product site & create dict for csv 
        for i, product in enumerate(items):
            link = 'https://prada.com' + product.get("href")
            print(f"Gathering product {i} {link}")
            response = requests.get(link, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            print("Success, scraping...")
            
            
            details = soup.find("div", "product-details-wrapper")
            detailList = details.find('ul')
            material = details.find_all('p', re.compile('text-paragraph'))[1].text
            description = details.find("p", re.compile("text-paragraph")).text
            
            # Assuming type is the only value hardcoded, search parameters should work for other collection categories, will continue later
            name = product.find("h3", "product-card__name").text
            id_ = detailList.li.text
            id_ = id_[id_.find(":") + 1 :].lstrip()
            price = int(product.find("p", "product-card__price--new").text.replace(",", "").strip("$"))
            material = material[material.find(": ") + 1 :].lstrip()
            firstColor = soup.find("div", {"data-element": "colorpicker"}).find("a").get("title").strip()
            firstSize = soup.find("ul", "size-picker-drawer__list").find(size_available).text.strip()
            firstDetail = detailList.find_all("li")[1].text.strip()
            
            item = {
                "name": name,
                "id": id_,
                "type": "Outerwear",
                "price": price,
                "material": material,
                "description": description,
                "colors": firstColor,
                "sizes": firstSize,
                "details": firstDetail,
            }
            
            # Appendings, using unique char and strip unnecessary spaces for easy text splitting from csv
            sizes = soup.find("ul", "size-picker-drawer__list").find_all(size_available)
            for size in sizes:
                if not item["sizes"].count(size.text) > 0:
                    item["sizes"] += "/" + size.text.strip()
            
            colors = soup.find("div", {"data-element": "colorpicker"}).find_all('a')
            for color in colors:
                if not item['colors'].count(color.get('title')) > 0:
                    item['colors'] += ',' + color.get('title').strip()
            
            for tag in detailList.find_all('li')[2:-2]:
                item['details'] += '|' + tag.text.strip()
            

                
            products.append(item)
            print(f"Progress: { round(((i+1) / amt) * 100, 1) }% ...")
        driver.close()
        csv = 'pradaProducts.csv'
    #For mnml for rn
    else:
        response = requests.get(mnml_denim)
        data = response.json()
        amt = len(data["products"])
        print(f"{amt} products found")
        
        for i, product in enumerate(data['products']):
            desc_html = product["body_html"]
            soup = BeautifulSoup(desc_html, "html.parser")
            rawDesc = soup.get_text()
            li = rawDesc.splitlines()
            if len(li[0]) > 1:
                description = li[0]
            else:
                description = li[1]
                
            
            name = product["title"][:product['title'].find(' -')]
            id_ = str(product["id"])
            type_ = product["product_type"]
            price = float(product["variants"][0]["price"])
            material = soup.find(lambda tag: tag.name == "li" and ("%" in tag.get_text() or re.compile("made from").search(tag.get_text())) ).text.replace("Composition: ", "").strip().lower()
            description = description.title()
            firstColor = product["variants"][0]["option1"]
            firstSize = product["variants"][0]['option2']
            imgCount = len(product["images"]) # Count for now, may use image recognition for unsupervised clustering patterns would b cool
            
            item = {
                "name": name,
                "id": id_,
                "type": type_,
                "price": price,
                "material": material,
                "description": description,
                "colors": firstColor,  # tbf
                "sizes": firstSize,  # tbf
                "imageCount": imgCount,
            }
            
            # Appendings
            for variant in product["variants"]:
                size = variant['option2']
                color = variant['option1']
                if not item['sizes'].count(size) > 0:
                    item["sizes"] += '/' + size
                if not item['colors'].count(color) > 0:
                    item["colors"] += ', ' + color
            
            products.append(item)
            print(f"Progress: {round(((i + 1) / amt) * 100, 1)}% ({i+1}/{amt})...")
            
        csv = "mnmlProducts.csv"
    
    df = pd.DataFrame(products)
    df.to_csv(csv)
    print("Saved")


if __name__ == "__main__":
    main()