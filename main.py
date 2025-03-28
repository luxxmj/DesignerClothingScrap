import pandas as pd
from bs4 import BeautifulSoup
import time
import re
import requests
from selenium.webdriver import Firefox, FirefoxOptions

# from selenium.webdriver.common.action_chains import ActionChains
# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import numpy as np

# Luxury clothing brands to scrape from; ranks wont go into any data just for organization
s_brands = ["Bottega Veneta", "Louis Vuitton"]
a_brands = ["Prada", "Marni"]
b_brands = ["Burberry", "YSL"]
c_brands = ["Versace", "Polo Ralph Lauren"]
# Street clothing brands to scrape from; ranks wont go into any data just for organization, tbf
ss_brands = ["MNML", ""]
aa_brands = ["", ""]
bb_brands = ["", ""]
cc_brands = ["", ""]

options = FirefoxOptions()
options.headless = True
driver = Firefox(options=options)

# Indicate brand and category
brand = "prada"
category = "leather clothing"

luxuryUrls = {
    "prada": {
        "outerwear": "https://www.prada.com/us/en/mens/ready-to-wear/outerwear/c/10136US",
        "denim": "https://www.prada.com/us/en/mens/ready-to-wear/denim/c/10131US",
        "suits": "https://www.prada.com/us/en/mens/ready-to-wear/suits/c/10139US",
        "leather clothing": "https://www.prada.com/us/en/mens/ready-to-wear/leather-clothing/c/10135US",
        "knitwear": "https://www.prada.com/us/en/mens/ready-to-wear/knitwear/c/10134US",
    },
    "bottega": {
        "outerwear": [
            "https://www.bottegaveneta.com/en-us/men/men-clothing/coats",
            "https://www.bottegaveneta.com/en-us/men/men-clothing/jackets",
        ]
    },
    "louis": {
        "outerwear": "https://us.louisvuitton.com/eng-us/men/ready-to-wear/coats/_/N-t1epdz97"
    },
    "burberry": {"outerwear": "https://us.burberry.com/l/mens-coats-jackets/"},
}

streetwearUrls = {
    "mnml": {"denim": "https://mnml.la/collections/denim/products.json?limit=1000"},
}


headers = {
    "User-Agent": ""  # Paste your user agent
}


# For excluding a certain nested listed item (unavailable size item)
def size_available(tag):
    return tag.name == "li" and not tag.find("button", disabled=True)


def main() -> None:
    products = []
    rand = np.random.uniform

    if brand == "prada":
        # Get page, accept cookies, and expand page to see all items
        driver.get(luxuryUrls["prada"][category])
        driver.implicitly_wait(5)
        time.sleep(2)

        try:
            button = driver.find_element(By.XPATH, "//*[@aria-label='Show more']")
        except:
            button = None
        driver.find_element(By.CLASS_NAME, "banner_cta").click()

        # Get expected product amount on page
        amtEle = driver.find_element(By.TAG_NAME, "p")
        amt = int(amtEle.text[: amtEle.text.find(" ")])
        print(f"{amt} {category} products")

        if button:
            button.click()

        h = 0
        prevCount = 0
        # Scroll page until all items found (infinite scrolling javascript)
        while True:
            soup = BeautifulSoup(driver.page_source, "lxml")
            items = soup.find_all("a", class_="h-full product-card__link")
            count = len(items)
            print(f"Found {count}/{amt}...")
            if not count >= amt:
                driver.execute_script(
                    f"window.scrollTo(0, (document.body.scrollHeight / 100) * {str(h * (10))} );"
                )
                time.sleep(0.5)
                h += 1
                if count > prevCount:
                    if prevCount > 0:
                        h = max(1, (h - 3))
                    prevCount = count
            else:
                break

        # For each product, request product site & create dict for csv
        for i, product in enumerate(items):
            link = "https://prada.com" + product.get("href")
            print(f"Gathering product {i} {link}")
            response = requests.get(link, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            print("Success, brand...")

            details = soup.find("div", "product-details-wrapper")
            detailList = details.find("ul")
            material = details.find_all("p", re.compile("text-paragraph"))[1].text
            description = details.find("p", re.compile("text-paragraph")).text

            # Assuming type is the only value hardcoded, search parameters should work for other collection categories, will continue later
            name = product.find("h3", "product-card__name").text
            id_ = detailList.li.text
            id_ = id_[id_.find(":") + 1 :].lstrip()
            price = float(
                product.find("p", "product-card__price--new")
                .text.replace(",", "")
                .strip("$")
            )
            material = material[material.find(": ") + 1 :].lstrip()
            firstColor = (
                soup.find("div", {"data-element": "colorpicker"})
                .find("a")
                .get("title")
                .strip()
            )
            firstSize = (
                soup.find("ul", "size-picker-drawer__list").find("li").text.strip()
            )
            firstDetail = detailList.find_all("li")[1].text.strip()

            item = {
                "name": name,
                "id": id_,
                "type": category.title(),
                "price": price,
                "material": material,
                "description": description,
                "colors": firstColor,
                "sizes": firstSize,
                "details": firstDetail,
            }

            # Appendings, using unique char and strip unnecessary spaces for easy text splitting from csv
            sizes = soup.find("ul", "size-picker-drawer__list").find_all("li")
            for size in sizes:
                if not item["sizes"].count(size.text) > 0:
                    item["sizes"] += "/" + size.text.strip()

            colors = soup.find("div", {"data-element": "colorpicker"}).find_all("a")
            for color in colors:
                if not item["colors"].count(color.get("title")) > 0:
                    item["colors"] += "," + color.get("title").strip()

            for tag in detailList.find_all("li")[2:-2]:
                item["details"] += "|" + tag.text.strip()

            products.append(item)
            print(f"Progress: {round(((i + 1) / amt) * 100, 1)}% ...")
    elif brand == "bottega":
        for i, page in enumerate(luxuryUrls["bv"][category]):
            driver.get(page)
            driver.implicitly_wait(4)
            # if i == 1:
            #     time.sleep(2)
            #     driver.find_element(By.ID, "onetrust-accept-btn-handler").click()

            amtEle = driver.find_element(By.CLASS_NAME, "c-filters__count")
            amt = int(amtEle.text.strip()[: amtEle.text.find(" ")])
            print(amt)

            h = 0
            prevCount = 0
            while True:
                soup = BeautifulSoup(driver.page_source, "lxml")
                items = soup.find_all("div", "l-productgrid__item")
                count = len(items)
                if not count == amt:
                    driver.execute_script(
                        f"window.scrollTo(0, (document.body.scrollHeight / 100) * {str(h * 10)} );"
                    )
                    time.sleep(1)
                    print(len(items))
                    h += 1
                    if count > prevCount:
                        if prevCount > 0:
                            h = 5
                        prevCount = count
                else:
                    break

            for i, product in enumerate(items):
                href = product.find("a").get("href")
                link = "https://www.bottegaveneta.com" + href

                print(f"Gathering product {i} {link}")
                response = requests.get(link, headers=headers)
                soup = BeautifulSoup(response.text, "html.parser")
                print("Success, brand...")

                detailContainer = soup.find(
                    "div", {"data-ref": "productContainerDetail"}
                )
                detailLi = detailContainer.find("div", {"id": "productLongDesc"})

                material = detailLi.find(
                    "li", "c-product__desccomposition"
                ).text.strip()

                description = detailContainer.find(
                    "div", "l-pdp__compactedlongdesc"
                ).text.strip()

                descExpandButton = detailContainer.find(
                    lambda tag: tag.name == "span"
                    and tag.get("class")
                    and "c-pdp-truncateddescription--expand" in tag.get("class")
                    and "u-hidden" not in tag.get("class")
                )
                if descExpandButton:
                    description += detailContainer.find(
                        lambda tag: tag.name == "span"
                        and tag.get("class")
                        and "c-pdp-truncateddescription" in tag.get("class")
                        and "--" not in tag.get("class")
                    ).text.rstrip()

                # Assuming type is the only value hardcoded, search parameters should work for other collection categories, will continue later
                name = detailContainer.find("h1", "c-product__name").text.strip()
                id_ = (
                    detailContainer.find("p", "c-product__id").find("span").text.strip()
                )
                price = float(
                    detailContainer.find("p", "c-price__value--current")
                    .text.replace(",", "")
                    .strip()
                    .strip("$ ")
                )
                material = material[material.find(": ") + 1 :].strip()
                firstColor = (
                    detailContainer.find("p", "c-swatches__item")
                    .find("span")
                    .text.strip()
                    .title()
                )
                firstSize = (
                    detailContainer.find("div", "c-customselect__menu")
                    .find_all("div")[0]
                    .find("span")
                    .text.strip()
                )
                descDetails = detailLi.find("p").text.splitlines()[1].split("• ")
                firstDetail = descDetails[1]

                item = {
                    "name": name,
                    "id": id_,
                    "type": category.title(),
                    "price": price,
                    "material": material,
                    "description": description,
                    "colors": firstColor,
                    "sizes": firstSize,
                    "details": firstDetail,
                }

                # Appendings, using unique char and strip unnecessary spaces for easy text splitting from csv
                sizes = detailContainer.find("div", "c-customselect__menu").find_all(
                    "div"
                )
                for size in sizes:
                    if not item["sizes"].count(size.find("span").text) > 0:
                        item["sizes"] += "/" + size.find("span").text.strip()

                colors = detailContainer.find_all("p", "c-swatches__item")
                for color in colors:
                    if (
                        not item["colors"].count(
                            color.find("span").text.strip().title()
                        )
                        > 0
                    ):
                        item["colors"] += "," + color.find("span").text.strip().title()

                for tag in descDetails[1:]:
                    item["details"] += "|" + tag

                products.append(item)
                print(f"Progress: {round(((i + 1) / amt) * 100, 1)}% ...")

    elif brand == "louis":
        driver.get(luxuryUrls["lv"][category])
        driver.implicitly_wait(4)

        time.sleep(rand(3.5, 4.5))
        driver.find_element(By.ID, "ucm-banner").find_element(
            By.TAG_NAME, "ul"
        ).find_elements(By.TAG_NAME, "a")[2].click()

        amt = 131  # Had to hardcode, no indication besides loading
        print(amt)

        h = 0
        prevCount = 0
        time.sleep(rand(2.0, 4.0))
        while True:
            soup = BeautifulSoup(driver.page_source, "lxml")
            items = soup.find_all("li", "lv-product-list__item")
            count = len(items)
            if not count == amt:
                driver.execute_script(
                    f"window.scrollTo(0, (document.body.scrollHeight / 100) * {str(h * (rand(5.0, 10.0)))} );"
                )
                time.sleep(rand(2.0, 4.0))

                moreButton = soup.find("div", "lv-paginated-list__button-wrap")

                if moreButton:
                    print(f"Clicking more {moreButton}")
                    driver.find_element(
                        By.CLASS_NAME, "lv-paginated-list__button-wrap"
                    ).button.click()

                print(len(items))
                h += 1
                if count > prevCount:
                    if prevCount > 0:
                        h = max(1, (h - 5))
                    prevCount = count

                if count == 0:
                    input()
                    return
            else:
                break

        for i, product in enumerate(items):
            href = product.find("div", "lv-product-card__name-wrapper").h2.a
            link = "https://us.louisvuitton.com/" + href.get("href")

            name = href.text.strip()

            price = round(
                float(
                    product.find("div", "lv-price lv-product-card__price body-s")
                    .span.text.strip(",")
                    .strip()
                    .strip("$ ")
                )
            )

            print(f"Gathering product {i} {link}")
            response = requests.get(link, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            print("Success, brand...")

            detailContainer = soup.find("div", "lv-expandable-panel__content")
            detailLi = detailContainer.find("ul")

            material = detailLi.find_all("li")[2].text.strip()

            description = detailContainer.find("p").text.strip().title()

            id_ = detailContainer.find("p", "c-product__id").find("span").text.strip()

            firstColor = detailLi.find_all("li")[1].text.strip()

            firstSize = (
                soup.find("div", "lv-product-variation-badges")
                .find("li")
                .a.span.text.strip()
            )
            firstDetail = detailLi.find("li").text.strip()

            item = {
                "name": name,
                "id": id_,
                "type": category.title(),
                "price": price,
                "material": material,
                "description": description,
                "colors": firstColor,
                "sizes": firstSize,
                "details": firstDetail,
            }

            # Appendings, using unique char and strip unnecessary spaces for easy text splitting from csv
            sizes = soup.find("div", "lv-product-variation-badges").find_all("li")
            for size in sizes:
                if not item["sizes"].count(size.a.span.text.strip()) > 0:
                    item["sizes"] += "/" + size.a.span.text.strip()

            for tag in detailLi.find_all("li")[3:]:
                item["details"] += "|" + tag.text.strip()

            products.append(item)
            print(f"Progress: {round(((i + 1) / amt) * 100, 1)}% ...")

    elif brand == "burberry":
        driver.get(luxuryUrls["bb"][category])
        driver.implicitly_wait(4)
        soup = BeautifulSoup(driver.page_source, "lxml")
        time.sleep(rand(1.0, 3.0))

        amt = int(soup.find("p", {"data-testid": "product-total"}).text.strip(" items"))
        print(amt)

        h = 0
        prevCount = 0
        while True:
            soup = BeautifulSoup(driver.page_source, "lxml")
            items = soup.find_all("li", "product-listing-shelf__product-card")
            count = len(items)
            if not count == amt:
                driver.execute_script(
                    f"window.scrollTo(0, (document.body.scrollHeight / 100) * {str(h * (rand(5.0, 8.0)))} );"
                )
                time.sleep(rand(0.0, 1.0))

                moreDiv = soup.find(
                    "div", "product-listing-shelf__view-more-wrapper--compact"
                )
                moreButton = moreDiv and moreDiv.find("button")

                if moreButton:
                    print(f"Clicking more {moreButton}")
                    driver.find_element(
                        By.CLASS_NAME,
                        "product-listing-shelf__view-more-wrapper--compact",
                    ).find_element(By.TAG_NAME, "button").click()

                print(len(items))
                h += 1
                if count > prevCount:
                    if prevCount > 0:
                        h = max(1, (h - 3))
                    prevCount = count

            else:
                break

        for i, product in enumerate(items):
            href = product.a
            link = "https://us.burberry.com/" + href.get("href")

            name = href.find("h2", "product-card-v2-title").text.strip()

            price = round(
                float(
                    href.find("span", "product-card-v2-price__current")
                    .text.replace(",", "")
                    .strip("$")
                )
            )

            colorVariants = href.find("ul", "product-card-v2-swatches__list")

            if colorVariants:
                firstColor = colorVariants.find_all("li")[0].img.get("alt")
                colors = colorVariants.find_all("li")[1:]
            else:
                firstColor = None
                colors = []

            print(f"Gathering product {i} {link}")
            response = requests.get(link, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            print("Success, brand...")

            if not firstColor:
                firstColor = soup.find(
                    "div", "product-swatches-panel__description"
                ).span.text

            detailContainer = soup.find("ul", "product-details-accordion").find_all(
                "li", "product-details-accordion__item"
            )
            detailLi = detailContainer[0]

            materials = detailContainer[2].find("ul").find_all("li")[:-2]

            material = materials[0].span.text.replace("–", "").strip()
            for mat in materials:
                mat = mat.span.text.replace("–", "").strip()
                if not material.count(mat) > 0:
                    material += ", " + mat

            description = detailLi.ul.li.span.text.strip().title()

            id_ = detailLi.ul.find_all("li")[-1].span.text.replace("– Item", "").strip()

            firstDetail = (
                detailLi.ul.find_all("li")[1].span.text.replace("–", "").strip()
            )

            driver.get(link)
            driver.implicitly_wait(3)

            driver.find_element(
                By.CLASS_NAME, "transactional-picker__options.size-picker__options"
            ).click()

            time.sleep(2)
            try:
                sizes = driver.find_element(
                    By.CLASS_NAME,
                    "size-picker__radio-type-selector.size-picker__radio-type-selector-column",
                ).find_elements(By.XPATH, "./*")
            except:
                driver.find_element(
                    By.CLASS_NAME, "transactional-picker__options.size-picker__options"
                ).click()
                time.sleep(3)
                sizes = driver.find_element(
                    By.CLASS_NAME,
                    "size-picker__radio-type-selector.size-picker__radio-type-selector-column",
                ).find_elements(By.XPATH, "./*")

            firstSize = (
                sizes[0].find_element(By.TAG_NAME, "input").get_attribute("value")
            )

            item = {
                "name": name,
                "id": id_,
                "type": category.title(),
                "price": price,
                "material": material,
                "description": description,
                "colors": firstColor,
                "sizes": firstSize,
                "details": firstDetail,
            }

            # Appendings, using unique char and strip unnecessary spaces for easy text splitting from csv
            for color in colors:
                item["colors"] += "/" + color.img.get("alt").strip()

            for size in sizes[1:]:
                size = size.find_element(By.TAG_NAME, "input").get_attribute("value")
                if not item["sizes"].count(size) > 0:
                    item["sizes"] += "/" + size

            for tag in detailLi.ul.find_all("li")[2:-2]:
                item["details"] += "|" + tag.span.text.replace("–", "").strip()

            products.append(item)
            print(f"Progress: {round(((i + 1) / amt) * 100, 1)}% ...")

    elif brand == "mnml":
        response = requests.get(streetwearUrls["mnml"][category])
        data = response.json()
        amt = len(data["products"])
        print(f"{amt} products found")

        for i, product in enumerate(data["products"]):
            desc_html = product["body_html"]
            soup = BeautifulSoup(desc_html, "html.parser")
            rawDesc = soup.get_text()
            li = rawDesc.splitlines()
            if len(li[0]) > 1:
                description = li[0]
            else:
                description = li[1]

            name = product["title"][: product["title"].find(" -")]
            id_ = str(product["id"])
            type_ = product["product_type"]
            price = float(product["variants"][0]["price"])
            material = (
                soup.find(
                    lambda tag: tag.name == "li"
                    and (
                        "%" in tag.get_text()
                        or re.compile("made from").search(tag.get_text())
                    )
                )
                .text.replace("Composition: ", "")
                .strip()
                .lower()
            )
            description = description.title()
            firstColor = product["variants"][0]["option1"]
            firstSize = product["variants"][0]["option2"]
            imgCount = len(
                product["images"]
            )  # Count for now, may use image recognition for unsupervised clustering patterns would b cool

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
                size = variant["option2"]
                color = variant["option1"]
                if not item["sizes"].count(size) > 0:
                    item["sizes"] += "/" + size
                if not item["colors"].count(color) > 0:
                    item["colors"] += ", " + color

            products.append(item)
            print(f"Progress: {round(((i + 1) / amt) * 100, 1)}% ({i + 1}/{amt})...")

    driver.close()
    csv = f"{brand.title()}/{brand}Products_{category.replace(' ', '-').title()}.csv"

    df = pd.DataFrame(products)
    df.to_csv(csv)
    print("Saved")


if __name__ == "__main__":
    main()
