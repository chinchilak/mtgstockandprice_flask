import asyncio
from playwright.async_api import async_playwright
from flask import Flask, render_template, request
import time

CR = "https://cernyrytir.cz/index.php3?akce=3"
BL = "https://www.blacklotus.cz/magic-kusove-karty/"
NG = "https://www.najada.games/mtg/singles/bulk-purchase"
COLS = ("Name", "Set", "Type", "Rarity", "Language", "Condition", "Stock", "Price")

app = Flask(__name__)

def flatten_nested_list(nested_list):
    flat_list = [item for sublist in nested_list for item in sublist]
    return flat_list

async def process_input_data(inputstring):
    return inputstring.strip().split('\n')

async def get_cerny_rytir_data(url, search_query):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.type('input[name="jmenokarty"]', search_query)
        await page.press('input[name="jmenokarty"]', 'Enter')
        await page.wait_for_load_state('domcontentloaded')

        tbody_elements = await page.locator('tbody').all()

        if len(tbody_elements) >= 7:
            tbody = tbody_elements[6]

            td_elements = await tbody.locator('td').all()

            data = []
            current_lines = []

            for td in td_elements:
                line = await td.inner_text()
                line = line.strip().replace('\xa0', ' ')
                if len(line) > 0:
                    current_lines.append(line)
                    if len(current_lines) == 6:
                        category_data = {
                            COLS[0]: current_lines[0],
                            COLS[1]: current_lines[1],
                            COLS[2]: current_lines[2],
                            COLS[3]: current_lines[3],
                            COLS[4]: "",
                            COLS[5]: "",
                            COLS[6]: current_lines[4],
                            COLS[7]: current_lines[5]}

                        data.append(category_data)
                        current_lines = []

        await browser.close()
        return data

async def get_black_lotus_data(url, search_query):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        await page.type('input[name="string"]', search_query)
        await page.press('input[name="string"]', 'Enter')
        await page.wait_for_load_state('domcontentloaded')

        div_elements = await page.query_selector_all('.products.products-block div')
        text_values = []

        for div_element in div_elements:
            text_values.append(await div_element.inner_text())

        await browser.close()

        filtered_data = [item.split('\n') for item in text_values if search_query.lower() in item.lower() and len(item.split('\n')) >= 4]

        unique_sublists = set()
        for sublist in filtered_data:
            unique_sublists.add(tuple(sublist))
        unique_sublists = [list(sublist) for sublist in unique_sublists]

        filtered_list = []
        for sublist in unique_sublists:
            filtered_sublist = [item for item in sublist if item and "DETAIL" not in item]
            while len(filtered_sublist) < 4:
                filtered_sublist.append('')

            edition_element = filtered_sublist[3]
            if " z edice " in edition_element:
                index = edition_element.find(' z edice ')
                if index != -1:
                    extracted_part = edition_element[index + len(' z edice '):]
                if extracted_part.endswith('.'):
                    extracted_part = extracted_part[:-1]
                filtered_sublist[3] = extracted_part

            qty_element = filtered_sublist[1]
            numeric_qty = ""
            if any(char.isdigit() for char in qty_element):
                for char in qty_element:
                    if char.isdigit():
                        numeric_qty += char
            if numeric_qty:
                filtered_sublist[1] = numeric_qty + " ks"
            else:
                filtered_sublist[1] = "0 ks"

            filtered_list.append(filtered_sublist)

        data = []

        for item in filtered_list:
            category_data = {
                COLS[0]: item[0],
                COLS[1]: item[3],
                COLS[2]: "",
                COLS[3]: "",
                COLS[4]: "",
                COLS[5]: "",
                COLS[6]: item[1],
                COLS[7]: item[2]}
            data.append(category_data)

        return data

async def get_najada_games_data(url: str, searchstring: str) -> list:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url)

        await page.wait_for_selector('textarea#cardData')
        await page.fill('textarea#cardData', searchstring)
        await page.click('div.my-5.Button.font-encodeCond.f-15.p-7-44.green')
        await page.wait_for_selector('.BulkPurchaseResult', state='visible')

        loose_card_elements = await page.query_selector_all('.BulkPurchaseResult .LooseCard')

        result_list = []
        headers = [COLS[5], COLS[6], COLS[7]]
        for element in loose_card_elements:
            card_info = {}
            card_info[COLS[0]] = await element.evaluate('(element) => element.querySelector(".title.font-encodeCond").textContent')
            card_info[COLS[1]] = await element.evaluate('(element) => element.querySelector(".expansionTitle.font-hind").textContent')
            card_info[COLS[3]] = await element.evaluate('(element) => element.querySelector(".rarity.font-hind.text-right").textContent')
            card_info[COLS[4]] = (await element.evaluate('(element) => element.querySelector(".name").textContent')).strip()

            details_text = (await element.evaluate('(element) => element.querySelector(".TabSwitchVertical").textContent')).strip()
            details_list = [item.strip() for item in details_text.split('\n') if item.strip()]
            details_list = [item[-2:] if "Wantlist " in item else item for item in details_list]
            details_list = [item for item in details_list if '+' not in item and '-' not in item and "r." not in item]
            if len(details_list) >= 2:
                details_list = details_list[1:]

            sublists = [details_list[i:i + 3] for i in range(0, len(details_list), 3)]

            for sublist in sublists:
                for i, col_header in enumerate(headers):
                    card_info[col_header] = sublist[i]
                result_list.append(card_info.copy())

        await browser.close()

        return result_list

async def main(inputlist, inpustring):
    start_time = time.time()
    try:
        print("Running Cerny Rytir script...")
        tasks_parallel_cerny_rytir = [get_cerny_rytir_data(CR, item) for item in inputlist]
        results_parallel_cerny_rytir = await asyncio.gather(*tasks_parallel_cerny_rytir)
        print(f"Cerny Rytir script completed in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        print(f"Error in Cerny Rytir script: {e}")
        results_parallel_cerny_rytir = []

    try:
        print("Running Black Lotus script...")
        tasks_parallel_black_lotus = [get_black_lotus_data(BL, item) for item in inputlist]
        results_parallel_black_lotus = await asyncio.gather(*tasks_parallel_black_lotus)
        print(f"Black Lotus script completed in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        print(f"Error in Black Lotus script: {e}")
        results_parallel_black_lotus = []

    try:
        print("Running Najada Games script...")
        result_sequence_najada_games = await get_najada_games_data(NG, inpustring)
        print(f"Najada Games script completed in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        print(f"Error in Najada Games script: {e}")
        result_sequence_najada_games = []

    print(f"All scripts completed in {time.time() - start_time:.2f} seconds.")

    return results_parallel_cerny_rytir, results_parallel_black_lotus, result_sequence_najada_games


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    input_string = request.form['input_string']
    input_list = asyncio.run(process_input_data(input_string))
    results_parallel_cerny_rytir, results_parallel_black_lotus, result_sequence_najada_games = asyncio.run(main(input_list, input_string))
    return render_template('result.html',
                           cr_results=flatten_nested_list(results_parallel_cerny_rytir),
                           bl_results=flatten_nested_list(results_parallel_black_lotus),
                           ng_results=result_sequence_najada_games)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=False)
