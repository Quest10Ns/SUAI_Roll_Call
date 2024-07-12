import time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--incognito")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
service = Service(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 15, poll_frequency=1)

def get_teachers():
    driver.get("https://guap.ru/rasp/")
    teachers = []
    for teacher in driver.find_elements("xpath", "//select[@name='ctl00$cphMain$ctl06']/option"):
        teachers.append([teacher.get_attribute("value"), teacher.text])

    return teachers[1:]

def get_schedule(teacher):
    driver.get(f'https://guap.ru/rasp/?p={teacher[0]}')
    pages = driver.page_source
    count = 0
    start = 0
    endLine = 0
    schedule = []
    for i in range(len(pages)):
        if pages[i:i+4] == '<h3>' and count == 0:
            start = i
            count = 1
        elif pages[i:i+31] == '</span></div></div></div></div>' and count == 1:
            endLine = i
            break
    pages = pages[start:endLine].split("<h3>")
    for page in pages:
        page = page.replace('<h4>', '--')
        for i in range(page.count('<')):
            start = page.find('<')
            end = page.find('>')
            page = page[:start:] + ' ' + page[end+1::]

        while '  ' in page:
            page = page.replace('  ', ' ')

        for i in range(page.count("Преподаватель:")):
            cnt = page.find("Преподаватель:")
            page = page[:cnt] + page[cnt + 15 + len(teacher[1]):]

        schedule.append(page.split("--"))

    return schedule[1:]

all_teacher = get_teachers()

for i in range(len(all_teacher)):
    name_file = 'Препод '+(all_teacher[i][1].split("-"))[0]
    with open(f'{name_file}.txt', 'w', encoding='utf-8') as gs:
        print(('Группа ' + all_teacher[i][1]+'\n'), file=gs)
        schedule_for_teacher = get_schedule(all_teacher[i])
        for day in schedule_for_teacher:
            for lessons in day:
                print(lessons, file=gs)
            print('\n', file=gs)
        print('\n', file=gs)